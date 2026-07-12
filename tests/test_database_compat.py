import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.connection import CompatConnection  # noqa: E402
from db.profiles import DatabaseProfile  # noqa: E402
from db.runtime_store import build_audit_result_row_payloads, persist_task_run_completion, update_task_runtime_state, upsert_task_report  # noqa: E402
from db.schema import init_db  # noqa: E402


def pg_profile() -> DatabaseProfile:
    return DatabaseProfile(
        "local_pg",
        "postgresql",
        {
            "type": "postgresql",
            "host": "127.0.0.1",
            "port": 5432,
            "database": "code_audit_test",
            "username": "demo",
            "password": "demo",
            "schema": "dwp",
        },
    )


class SequenceCursor:
    def __init__(self):
        self.description = None
        self.executed = []
        self.rowcount = 1
        self.fetchall_queue = []
        self.fetchone_queue = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))
        if "RETURNING id" in sql:
            self.description = [("id",)]
            self.fetchone_queue.append((42,))
        elif "SELECT report_json" in sql:
            self.description = [("report_json",)]
            self.fetchone_queue.append(('{"ok": true}',))
        else:
            self.description = None

    def executemany(self, sql, param_sets):
        self.executed.append((sql, list(param_sets)))
        self.rowcount = len(param_sets)

    def fetchone(self):
        return self.fetchone_queue.pop(0) if self.fetchone_queue else None

    def fetchall(self):
        return self.fetchall_queue.pop(0) if self.fetchall_queue else []

    def close(self):
        pass


class SequenceConnection:
    def __init__(self):
        self.cursor_obj = SequenceCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class DatabaseCompatTests(unittest.TestCase):
    def test_execute_insert_uses_returning_id(self):
        fake = SequenceConnection()
        with patch("db.connection.connect", return_value=fake):
            inserted_id = CompatConnection(pg_profile()).execute(
                "INSERT INTO {{table:projects}} (name) VALUES (?)",
                ("demo",),
                expect_lastrowid=True,
            ).lastrowid
        self.assertEqual(inserted_id, 42)
        self.assertEqual(fake.cursor_obj.executed[-1], ("INSERT INTO dwp.p_audit_project_config (name) VALUES (%s) RETURNING id", ("demo",)))

    def test_upsert_task_report_uses_active_profile_connection(self):
        fake = SequenceConnection()
        with patch("db.connection.resolve_profile", return_value=pg_profile()), patch("db.connection.connect", return_value=fake):
            upsert_task_report(3, '{"ok": true}', "2026-07-09 12:00:00")
        statements = [sql for sql, _ in fake.cursor_obj.executed]
        self.assertEqual(
            statements,
            [
                "DELETE FROM dwp.p_audit_run_report WHERE task_id = %s",
                "INSERT INTO dwp.p_audit_run_report (task_id, report_json, created_at) VALUES (%s, %s, %s)",
            ],
        )

    def test_persist_task_run_completion_uses_same_runtime_tables(self):
        fake = SequenceConnection()
        with patch("db.connection.resolve_profile", return_value=pg_profile()), patch("db.connection.connect", return_value=fake):
            persist_task_run_completion(
                5,
                status="pass",
                duration="2s",
                finished_at="2026-07-09 12:00:00",
                error=None,
                progress=100,
                step="completed",
                logs=[{"msg": "done"}],
                report={"task": {"status": "pass"}},
            )
        statements = [sql.strip() for sql, _ in fake.cursor_obj.executed]
        self.assertEqual(len(statements), 3)
        self.assertTrue(statements[0].startswith("UPDATE dwp.p_audit_run"))
        self.assertIn("SET status = %s, duration = %s, finished_at = %s, error = %s, progress = %s, step = %s, logs_json = %s", statements[0])
        self.assertEqual(statements[1], "DELETE FROM dwp.p_audit_run_report WHERE task_id = %s")
        self.assertEqual(statements[2], "INSERT INTO dwp.p_audit_run_report (task_id, report_json, created_at) VALUES (%s, %s, %s)")

    def test_update_task_runtime_state_renders_runtime_table_for_postgres(self):
        fake = SequenceConnection()
        with patch("db.connection.resolve_profile", return_value=pg_profile()), patch("db.connection.connect", return_value=fake):
            update_task_runtime_state(5, "[]", progress=5, step="loading")
        self.assertEqual(
            fake.cursor_obj.executed[-1],
            (
                "UPDATE dwp.p_audit_run SET logs_json = %s, progress = %s, step = %s WHERE id = %s",
                ("[]", 5, "loading", 5),
            ),
        )

    def test_build_audit_result_row_payloads_normalizes_legacy_defaults(self):
        payloads = build_audit_result_row_payloads(8, {"python": [{"file": "demo.py", "line": None, "rule": None, "level": "", "msg": None}]})
        self.assertEqual(payloads, [(8, "python", "demo.py", 0, "", "info", "")])

    def test_init_db_only_initializes_runtime_tables(self):
        with patch("db.schema.ensure_runtime_tables") as ensure_runtime_tables:
            init_db()
        ensure_runtime_tables.assert_called_once_with(None, runner=None)


if __name__ == "__main__":
    unittest.main()
