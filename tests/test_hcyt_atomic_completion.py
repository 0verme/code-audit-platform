import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
import app.db.connection as db_connection  # noqa: E402
import app.db.runtime_store as runtime_store  # noqa: E402
from app.db.schema import init_db  # noqa: E402


class InjectedPersistenceFailure(RuntimeError):
    pass


class _FaultInjectingConnection:
    def __init__(self, connection, fail_when, events=None):
        self._connection = connection
        self._fail_when = fail_when
        self._events = events

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._events is not None:
            self._events.append("rollback" if exc_type else "commit")
        return self._connection.__exit__(exc_type, exc, tb)

    def execute(self, sql, params=(), **kwargs):
        if self._fail_when(sql, params):
            raise InjectedPersistenceFailure("injected persistence failure")
        return self._connection.execute(sql, params, **kwargs)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class HcytAtomicCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "runtime.sqlite"
        self.db_path_patch = patch.object(db_connection, "DB_PATH", self.db_path)
        self.db_path_patch.start()
        init_db()
        self.task_id = self._insert_task()
        self.addCleanup(self.db_path_patch.stop)
        self.addCleanup(self.tempdir.cleanup)

    def _insert_task(self):
        with db_connection.get_connection() as connection:
            return connection.execute(
                """INSERT INTO {{table:audit_tasks}} (
                    repo, workflow, status, revision, author, started_at, duration, ai_enabled, debug_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("svn://example/hcyt", "hcyt", "running", "r1", "tester", "2026-07-11 10:00:00", "", 0, 0),
                expect_lastrowid=True,
            ).lastrowid

    def _run(self):
        return audit_engine.TaskRun(self.task_id, "svn://example/hcyt", "hcyt")

    @staticmethod
    def _row(message="new finding"):
        return {"file": "demo.sql", "line": 7, "rule": "rule-a", "level": "warn", "msg": message}

    def _report(self, status="pass", grouped=None):
        grouped = grouped if grouped is not None else {"dws": [self._row()]}
        return {
            "task": {"status": status, "workflow": "HCYT"},
            **{category: grouped.get(category, []) for category in ("dws", "hive", "python", "sbin", "config", "recv")},
            "schedule": {"summary": {}, "tables": {}, "rows": [], "rowStates": {}},
            "lineageSummary": {"resultTables": [], "warnings": []},
            "assetIssues": [],
            "unifiedAssetIssues": [],
        }

    def _seed_old_state(self):
        runtime_store.upsert_task_report(self.task_id, '{"version":"old"}', "2026-07-11 10:00:00")
        runtime_store.replace_audit_results(self.task_id, {"old": [self._row("old finding")]})

    def _state(self):
        return (
            dict(runtime_store.get_audit_task(self.task_id)),
            runtime_store.get_task_report_payload(self.task_id),
            [dict(row) for row in runtime_store.list_audit_results(self.task_id)],
        )

    def _faulty_connections(self, fail_when, events=None):
        original = runtime_store.get_connection
        return patch.object(
            runtime_store,
            "get_connection",
            side_effect=lambda *args, **kwargs: _FaultInjectingConnection(original(*args, **kwargs), fail_when, events),
        )

    def test_complete_hcyt_commits_task_report_and_rows_atomically_before_memory_finalization(self):
        self._seed_old_state()
        run = self._run()
        report = self._report()
        legacy_completion = Mock()
        legacy_results = Mock()
        events = []
        original_set_partial = run.set_partial
        run.set_partial = lambda key, value: (
            events.append("final_ready") if key == "finalReport" else None,
            original_set_partial(key, value),
        )[-1]

        with self._faulty_connections(lambda _sql, _params: False, events), patch.object(
            audit_engine, "persist_task_run_completion", legacy_completion
        ), patch.object(audit_engine, "replace_audit_results", legacy_results):
            run.finish("pass", report=report)

        task, stored_report, rows = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(stored_report, report)
        self.assertEqual([(row["category"], row["file_name"], row["line_no"], row["message"]) for row in rows], [
            ("dws", "demo.sql", 7, "new finding")
        ])
        self.assertEqual(events, ["commit", "final_ready"])
        legacy_completion.assert_not_called()
        legacy_results.assert_not_called()
        self.assertEqual(run.run_state.status.value, "success")
        self.assertEqual(run.run_state.partial_report["finalReport"], report)

    def test_empty_hcyt_results_clear_old_rows(self):
        self._seed_old_state()
        run = self._run()

        run.finish("pass", report=self._report(grouped={}))

        task, report, rows = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(report["dws"], [])
        self.assertEqual(rows, [])

    def test_pass_warn_and_fail_use_atomic_completion_without_changing_verdict(self):
        for verdict in ("pass", "warn", "fail"):
            with self.subTest(verdict=verdict):
                run = self._run()
                run.finish(verdict, report=self._report(status=verdict))
                task, report, _rows = self._state()
                self.assertEqual(task["status"], verdict)
                self.assertEqual(report["task"]["status"], verdict)

    def test_report_results_and_task_failures_roll_back_without_legacy_fallback(self):
        cases = (
            ("report", lambda sql, _params: "INSERT INTO {{table:task_reports}}" in sql),
            ("results", lambda sql, _params: "INSERT INTO {{table:audit_results}}" in sql),
            ("task", lambda sql, _params: "UPDATE {{table:audit_tasks}}" in sql),
        )
        for name, fail_when in cases:
            with self.subTest(stage=name):
                self._seed_old_state()
                run = self._run()
                legacy_completion = Mock()
                with self._faulty_connections(fail_when), patch.object(
                    audit_engine, "persist_task_run_completion", legacy_completion
                ):
                    with self.assertRaises(InjectedPersistenceFailure):
                        run.finish("pass", report=self._report())

                task, report, rows = self._state()
                self.assertEqual(task["status"], "running")
                self.assertEqual(report, {"version": "old"})
                self.assertEqual([row["message"] for row in rows], ["old finding"])
                self.assertNotIn("finalReport", run.run_state.partial_report)
                self.assertNotEqual(run.run_state.status.value, "success")
                legacy_completion.assert_not_called()

    def test_early_failure_without_report_stays_on_legacy_failure_path(self):
        run = self._run()
        atomic_completion = Mock()
        legacy_completion = Mock()
        with patch.object(audit_engine, "persist_task_completion_atomic", atomic_completion), patch.object(
            audit_engine, "persist_task_run_completion", legacy_completion
        ):
            run.finish("fail", error="source unavailable")

        atomic_completion.assert_not_called()
        legacy_completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()
