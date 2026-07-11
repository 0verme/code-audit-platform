"""A6-1 contract for the new atomic repository API.

The A5 baseline keeps characterizing the legacy completion path.  These tests
exercise only the new capability; A6-2/A6-3 will migrate production callers.
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

import db.connection as db_connection  # noqa: E402
import db.runtime_store as runtime_store  # noqa: E402
from db.schema import init_db  # noqa: E402


class InjectedPersistenceFailure(RuntimeError):
    pass


class _FaultInjectingConnection:
    def __init__(self, connection, fail_when, observations):
        self._connection = connection
        self._fail_when = fail_when
        self._observations = observations

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self._observations.append("rollback")
            self._connection.rollback()
        else:
            self._observations.append("commit")
            self._connection.commit()
        self.close()
        return False

    def close(self):
        self._observations.append("closed")
        return self._connection.close()

    def execute(self, sql, params=(), **kwargs):
        if self._fail_when(sql, params):
            raise InjectedPersistenceFailure("injected persistence failure")
        return self._connection.execute(sql, params, **kwargs)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class AtomicTaskCompletionRepositoryTests(unittest.TestCase):
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
                ("svn://example/task", "hcyt", "running", "r1", "tester", "2026-07-11 10:00:00", "", 0, 0),
                expect_lastrowid=True,
            ).lastrowid

    @staticmethod
    def _row(message):
        return {"file": "demo.sql", "line": 7, "rule": "rule", "level": "warn", "msg": message}

    def _seed_old_state(self):
        runtime_store.upsert_task_report(self.task_id, json.dumps({"version": "old"}), "2026-07-11 10:00:00")
        runtime_store.replace_audit_results(self.task_id, {"old": [self._row("old")]})

    def _complete(self, report=None, results=None, **overrides):
        args = {
            "status": "pass", "duration": "1s", "finished_at": "2026-07-11 10:01:00", "error": None,
            "progress": 100, "step": "completed", "logs": [{"msg": "done"}],
            "report": report or {"version": "new"}, "audit_results": results if results is not None else {"sql": [self._row("new")]},
        }
        args.update(overrides)
        return runtime_store.persist_task_completion_atomic(self.task_id, **args)

    def _state(self):
        return (
            dict(runtime_store.get_audit_task(self.task_id)),
            runtime_store.get_task_report_payload(self.task_id),
            [dict(row) for row in runtime_store.list_audit_results(self.task_id)],
        )

    def _faulty_connections(self, fail_when):
        observations = []
        original = runtime_store.get_connection

        def factory(*args, **kwargs):
            observations.append("opened")
            return _FaultInjectingConnection(original(*args, **kwargs), fail_when, observations)

        return observations, patch.object(runtime_store, "get_connection", side_effect=factory)

    def test_commits_task_report_and_results_together(self):
        self._seed_old_state()
        result = self._complete(results={"sql": [self._row("new one"), self._row("new two")]})
        task, report, results = self._state()
        self.assertEqual(result, runtime_store.AtomicTaskCompletionResult(self.task_id, True, 2))
        self.assertEqual(task["status"], "pass")
        self.assertEqual(report, {"version": "new"})
        self.assertEqual([row["message"] for row in results], ["new one", "new two"])

    def test_report_failure_rolls_back_everything(self):
        self._seed_old_state()
        observations, connection_patch = self._faulty_connections(lambda sql, _p: "INSERT INTO {{table:task_reports}}" in sql)
        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            self._complete()
        task, report, results = self._state()
        self.assertEqual(task["status"], "running")
        self.assertEqual(report, {"version": "old"})
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "rollback", "closed"])

    def test_results_failure_after_delete_rolls_back_everything(self):
        self._seed_old_state()
        observations, connection_patch = self._faulty_connections(lambda sql, _p: "INSERT INTO {{table:audit_results}}" in sql)
        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            self._complete()
        task, report, results = self._state()
        self.assertEqual(task["status"], "running")
        self.assertEqual(report, {"version": "old"})
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "rollback", "closed"])

    def test_final_task_update_failure_rolls_back_report_and_results(self):
        self._seed_old_state()
        observations, connection_patch = self._faulty_connections(lambda sql, _p: "UPDATE {{table:audit_tasks}}" in sql)
        with connection_patch, self.assertRaises(InjectedPersistenceFailure):
            self._complete()
        task, report, results = self._state()
        self.assertEqual(task["status"], "running")
        self.assertEqual(report, {"version": "old"})
        self.assertEqual([row["message"] for row in results], ["old"])
        self.assertEqual(observations, ["opened", "rollback", "closed"])

    def test_missing_or_invalid_task_writes_nothing(self):
        with self.assertRaises(runtime_store.TaskCompletionValidationError):
            runtime_store.persist_task_completion_atomic(9999, status="pass", duration="1s", finished_at="now", error=None,
                progress=100, step="completed", logs=[], report={"version": "new"}, audit_results={})
        with self.assertRaises(runtime_store.TaskCompletionValidationError):
            runtime_store.persist_task_completion_atomic("bad", status="pass", duration="1s", finished_at="now", error=None,
                progress=100, step="completed", logs=[], report={"version": "new"}, audit_results={})
        self.assertIsNone(runtime_store.get_task_report_payload(self.task_id))
        self.assertEqual(runtime_store.list_audit_results(self.task_id), [])

    def test_empty_results_delete_old_rows_and_complete_task(self):
        self._seed_old_state()
        result = self._complete(results={})
        task, report, results = self._state()
        self.assertEqual(result.results_written, 0)
        self.assertEqual(task["status"], "pass")
        self.assertEqual(report, {"version": "new"})
        self.assertEqual(results, [])

    def test_replays_replace_the_single_report_and_result_set(self):
        self._complete(report={"version": "one"}, results={"sql": [self._row("one")]})
        self._complete(report={"version": "one"}, results={"sql": [self._row("one")]})
        _task, report, results = self._state()
        self.assertEqual(report, {"version": "one"})
        self.assertEqual([row["message"] for row in results], ["one"])
        self._complete(report={"version": "two"}, results={"sql": [self._row("two")]}, finished_at="2026-07-11 10:02:00")
        task, report, results = self._state()
        self.assertEqual(task["finished_at"], "2026-07-11 10:02:00")
        self.assertEqual(report, {"version": "two"})
        self.assertEqual([row["message"] for row in results], ["two"])

    def test_uses_one_connection_one_commit_and_closes_it(self):
        observations, connection_patch = self._faulty_connections(lambda _sql, _p: False)
        with connection_patch:
            self._complete()
        self.assertEqual(observations, ["opened", "commit", "closed"])


if __name__ == "__main__":
    unittest.main()
