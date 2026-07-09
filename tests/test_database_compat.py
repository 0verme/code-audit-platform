import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database  # noqa: E402
from db.profiles import DatabaseProfile  # noqa: E402


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
        if "SELECT COUNT(*) FROM dwp.p_audit_project_config" in sql:
            self.description = [("count",)]
            self.fetchone_queue.append((0,))
        elif "RETURNING id" in sql:
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
        with patch("database.connect", return_value=fake):
            inserted_id = database.CompatConnection(pg_profile()).execute(
                "INSERT INTO {{table:projects}} (name) VALUES (?)",
                ("demo",),
                expect_lastrowid=True,
            ).lastrowid
        self.assertEqual(inserted_id, 42)
        self.assertEqual(fake.cursor_obj.executed[-1], ("INSERT INTO dwp.p_audit_project_config (name) VALUES (%s) RETURNING id", ("demo",)))

    def test_upsert_task_report_uses_active_profile_connection(self):
        fake = SequenceConnection()
        with patch("database.resolve_profile", return_value=pg_profile()), patch("database.connect", return_value=fake):
            database.upsert_task_report(3, '{"ok": true}', "2026-07-09 12:00:00")
        statements = [sql for sql, _ in fake.cursor_obj.executed]
        self.assertEqual(
            statements,
            [
                "DELETE FROM dwp.p_audit_run_report WHERE task_id = %s",
                "INSERT INTO dwp.p_audit_run_report (task_id, report_json, created_at) VALUES (%s, %s, %s)",
            ],
        )

    def test_init_db_initializes_schema_and_seeds_demo_rows(self):
        fake = SequenceConnection()
        with patch("database.resolve_profile", return_value=pg_profile()), patch("database.connect", return_value=fake), patch("database.initialize_schema") as init_schema:
            database.init_db()
        init_schema.assert_called_once()
        executed_sql = [sql for sql, _ in fake.cursor_obj.executed]
        self.assertIn("SELECT COUNT(*) FROM dwp.p_audit_project_config", executed_sql[0])
        self.assertTrue(any("INSERT INTO dwp.p_audit_project_config" in sql for sql in executed_sql))
        self.assertTrue(any("INSERT INTO dwp.p_audit_run" in sql for sql in executed_sql))
        self.assertTrue(any("INSERT INTO dwp.fine_report_items" in sql for sql in executed_sql))


if __name__ == "__main__":
    unittest.main()
