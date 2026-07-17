"""Characterization baseline for Phase A5 task-completion persistence.

These assertions intentionally document today's non-atomic behaviour.  They
must be revised when the A6 atomic completion protocol is implemented.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
import app.db.connection as db_connection  # noqa: E402
import app.db.runtime_store as runtime_store  # noqa: E402
from app.db.schema import init_db  # noqa: E402


class InjectedPersistenceFailure(RuntimeError):
    """A deliberate, SQL-semantic persistence failure used only by A5 tests."""


class _FaultInjectingConnection:
    def __init__(self, connection, fail_when, observations):
        self._connection = connection
        self._fail_when = fail_when
        self._observations = observations

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._observations.append("rollback" if exc_type else "commit")
        return self._connection.__exit__(exc_type, exc, tb)

    def execute(self, sql, params=(), **kwargs):
        if self._fail_when(sql, params):
            raise InjectedPersistenceFailure("injected persistence failure")
        return self._connection.execute(sql, params, **kwargs)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class TaskCompletionAtomicityBaselineTests(unittest.TestCase):
    """Real SQLite state checks; none infer outcomes from mock call counts."""

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
                """
                INSERT INTO {{table:audit_tasks}} (
                    repo, workflow, status, revision, author, started_at, duration,
                    ai_enabled, debug_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("svn://example/task", "hcyt", "running", "r1", "tester", "2026-07-11 10:00:00", "", 0, 0),
                expect_lastrowid=True,
            ).lastrowid

    def _seed_report(self, version="old"):
        runtime_store.upsert_task_report(self.task_id, json.dumps({"version": version}), "2026-07-11 10:00:00")

    def _seed_results(self, version="old"):
        runtime_store.replace_audit_results(self.task_id, {"old": [self._result(version)]})

    @staticmethod
    def _result(message):
        return {"file": "demo.sql", "rule": "rule", "level": "warn", "msg": message}

    def _state(self):
        task = runtime_store.get_audit_task(self.task_id)
        report = runtime_store.get_task_report_payload(self.task_id)
        results = [dict(row) for row in runtime_store.list_audit_results(self.task_id)]
        return dict(task), report, results

    def _faulty_runtime_connections(self, fail_when):
        observations = []
        original_get_connection = runtime_store.get_connection

        def factory(*args, **kwargs):
            observations.append("opened")
            return _FaultInjectingConnection(original_get_connection(*args, **kwargs), fail_when, observations)

        return observations, patch.object(runtime_store, "get_connection", side_effect=factory)

    def _complete(self, report, finished_at="2026-07-11 10:01:00"):
        runtime_store.persist_task_run_completion(
            self.task_id, status="pass", duration="1s", finished_at=finished_at,
            error=None, progress=100, step="completed", logs=[{"msg": "done"}], report=report,
        )

    def test_current_completion_success_path_persists_terminal_task_report_and_results(self):
        """Characterization baseline for Phase A5; retain as the A6 success-path contract."""
        report = {"task": {"status": "pass"}, "version": "new"}
        grouped = {"sql": [self._result("new one"), self._result("new two")]}

        self._complete(report)
        runtime_store.replace_audit_results(self.task_id, grouped)

        task, stored_report, results = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(stored_report, report)
        self.assertEqual([row["message"] for row in results], ["new one", "new two"])
        self.assertEqual(len(results), 2)
        self.assertEqual(json.loads(runtime_store.get_task_report_row(self.task_id)["report_json"])["version"], "new")

    def test_current_completion_keeps_task_terminal_when_report_write_fails(self):
        """Characterization baseline: independent task commit survives report failure; reverse in A6."""
        self._seed_report()
        self._seed_results()
        observations, connection_patch = self._faulty_runtime_connections(
            lambda sql, _params: "INSERT INTO {{table:task_reports}}" in sql
        )

        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            self._complete({"version": "new"})

        task, report, results = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(report, {"version": "old"})
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "commit", "opened", "rollback"])

    def test_current_report_delete_then_insert_failure_rolls_back_old_report(self):
        """Characterization baseline: this local SQLite transaction rolls back, but not prior task commits."""
        self._seed_report()
        observations, connection_patch = self._faulty_runtime_connections(
            lambda sql, _params: "INSERT INTO {{table:task_reports}}" in sql
        )

        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            runtime_store.upsert_task_report(self.task_id, json.dumps({"version": "new"}), "2026-07-11 10:01:00")

        _task, report, _results = self._state()
        self.assertEqual(report, {"version": "old"})
        self.assertEqual(observations, ["opened", "rollback"])

    def test_current_results_replace_failure_restores_old_rows_in_its_local_transaction(self):
        """Characterization baseline: SQLite rolls back delete plus partial inserts; reverse only if protocol changes."""
        self._seed_results()
        inserted = 0

        def fail_on_second_result_insert(sql, _params):
            nonlocal inserted
            if "INSERT INTO {{table:audit_results}}" in sql:
                inserted += 1
                return inserted == 2
            return False

        observations, connection_patch = self._faulty_runtime_connections(fail_on_second_result_insert)
        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            runtime_store.replace_audit_results(self.task_id, {"sql": [self._result("new one"), self._result("new two")]})

        _task, _report, results = self._state()
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "rollback"])

    def test_current_report_can_commit_before_a_later_results_failure(self):
        """Characterization baseline: callers can expose a new report with old legacy results; reverse in A6."""
        self._seed_results()
        self._complete({"version": "new"})
        observations, connection_patch = self._faulty_runtime_connections(
            lambda sql, _params: "INSERT INTO {{table:audit_results}}" in sql
        )
        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            runtime_store.replace_audit_results(self.task_id, {"sql": [self._result("new")]})

        task, report, results = self._state()
        self.assertEqual(task["status"], "pass")
        self.assertEqual(report, {"version": "new"})
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "rollback"])

    def test_current_repeated_completion_replaces_rows_but_is_not_explicitly_idempotent(self):
        """Characterization baseline: delete/insert gives one visible version, without a completion version or CAS."""
        self._complete({"version": "one"}, "2026-07-11 10:01:00")
        runtime_store.replace_audit_results(self.task_id, {"sql": [self._result("one")]})
        self._complete({"version": "two"}, "2026-07-11 10:02:00")
        runtime_store.replace_audit_results(self.task_id, {"sql": [self._result("two")]})

        task, report, results = self._state()
        self.assertEqual(task["finished_at"], "2026-07-11 10:02:00")
        self.assertEqual(report, {"version": "two"})
        self.assertEqual([row["message"] for row in results], ["two"])
        self.assertEqual(len(results), 1)

    def test_legacy_task_run_marks_memory_terminal_before_persistence_failure(self):
        """Characterization baseline for unmigrated legacy completion paths."""
        run = audit_engine.TaskRun(999, "svn://example/task", "fine-report")
        with patch.object(audit_engine, "persist_task_run_completion", side_effect=InjectedPersistenceFailure("boom")):
            with self.assertRaises(InjectedPersistenceFailure):
                run.finish("pass", report={"task": {"status": "pass"}})

        self.assertEqual(run.run_state.status.value, "success")
        self.assertTrue(run.run_state.finished_at is not None)


if __name__ == "__main__":
    unittest.main()
