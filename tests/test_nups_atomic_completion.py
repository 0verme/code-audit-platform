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
    def __init__(self, connection, fail_when, observations=None):
        self._connection = connection
        self._fail_when = fail_when
        self._observations = observations

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._observations is not None:
            self._observations.append("rollback" if exc_type else "commit")
        return self._connection.__exit__(exc_type, exc, tb)

    def execute(self, sql, params=(), **kwargs):
        if self._fail_when(sql, params):
            raise InjectedPersistenceFailure("injected persistence failure")
        return self._connection.execute(sql, params, **kwargs)

    def executemany(self, sql, param_sets):
        rows = list(param_sets)
        if any(self._fail_when(sql, params) for params in rows):
            raise InjectedPersistenceFailure("injected persistence failure")
        return self._connection.executemany(sql, rows)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class NupsAtomicCompletionTests(unittest.TestCase):
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
                ("svn://example/nups", "nups", "running", "r1", "tester", "2026-07-11 10:00:00", "", 0, 0),
                expect_lastrowid=True,
            ).lastrowid

    def _run(self):
        return audit_engine.TaskRun(self.task_id, "svn://example/nups", "nups")

    @staticmethod
    def _report(status="pass", messages=None):
        messages = messages if messages is not None else [{"level": "warn", "msg": "new finding"}]
        return {
            "task": {"status": status, "workflow": "NUPS"},
            "sqlChecks": [{"script": "query.sql", "messages": messages}],
            "pyScripts": [],
            "assetIssues": [],
            "unifiedAssetIssues": [],
        }

    @staticmethod
    def _old_row():
        return {"file": "old.sql", "rule": "old", "level": "warn", "msg": "old finding"}

    def _seed_old_state(self):
        runtime_store.upsert_task_report(self.task_id, '{"version":"old"}', "2026-07-11 10:00:00")
        runtime_store.replace_audit_results(self.task_id, {"old": [self._old_row()]})

    def _state(self):
        return (
            dict(runtime_store.get_audit_task(self.task_id)),
            runtime_store.get_task_report_payload(self.task_id),
            [dict(row) for row in runtime_store.list_audit_results(self.task_id)],
        )

    def _faulty_connections(self, fail_when, observations=None):
        original = runtime_store.get_connection

        def factory(*args, **kwargs):
            if observations is not None:
                observations.append("opened")
            return _FaultInjectingConnection(original(*args, **kwargs), fail_when, observations)

        return patch.object(runtime_store, "get_connection", side_effect=factory)

    def test_complete_nups_commits_report_and_legacy_rows_atomically(self):
        self._seed_old_state()
        run = self._run()
        report = self._report()
        legacy_completion = Mock()
        observations = []

        with self._faulty_connections(lambda _sql, _params: False, observations), patch.object(
            audit_engine, "persist_task_run_completion", legacy_completion
        ):
            run.finish("pass", report=report)

        task, stored_report, rows = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(stored_report, report)
        self.assertEqual([(row["category"], row["file_name"], row["message"]) for row in rows], [
            ("nups", "query.sql", "new finding")
        ])
        legacy_completion.assert_not_called()
        self.assertEqual(observations, ["opened", "commit"])
        self.assertEqual(run.run_state.status.value, "success")

    def test_empty_nups_results_clear_prior_legacy_rows(self):
        self._seed_old_state()
        run = self._run()
        report = self._report(messages=[])

        run.finish("pass", report=report)

        task, stored_report, rows = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(stored_report, report)
        self.assertEqual(rows, [])

    def test_pass_warn_and_fail_verdicts_keep_their_existing_status(self):
        for verdict in ("pass", "warn", "fail"):
            with self.subTest(verdict=verdict):
                run = self._run()
                report = self._report(verdict)
                run.finish(verdict, report=report)
                task, stored_report, _rows = self._state()
                self.assertEqual(task["status"], verdict)
                self.assertEqual(stored_report["task"]["status"], verdict)

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
                self.assertEqual(task["status"], "fail")
                self.assertEqual(task["step"], "persistence_failed")
                self.assertEqual(report, {"version": "old"})
                self.assertEqual([row["message"] for row in rows], ["old finding"])
                legacy_completion.assert_not_called()
                self.assertEqual(run.run_state.status.value, "failed")
                self.assertEqual(run.run_state.get_task("summary").status.value, "failed")

    def test_early_failure_without_a_report_stays_on_legacy_path(self):
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
