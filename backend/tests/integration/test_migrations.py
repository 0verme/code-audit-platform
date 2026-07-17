import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.profiles import DatabaseProfile
from app.migrations import MigrationRunner


class MigrationIntegrationTests(unittest.TestCase):
    def test_empty_sqlite_database_migrates_to_latest_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "audit.db"
            connection = sqlite3.connect(database)
            try:
                profile = DatabaseProfile("test", "sqlite", {"type": "sqlite", "path": str(database)})
                root = Path(__file__).resolve().parents[2] / "migrations"
                runner = MigrationRunner(connection, "sqlite", root, profile)
                self.assertEqual(runner.apply(), ["0001", "0002", "0003"])
                self.assertEqual(runner.apply(), [])
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                self.assertIn("schema_migrations", tables)
                self.assertIn("p_audit_run", tables)
                self.assertEqual(set(runner.status().applied), {"0001", "0002", "0003"})
                columns = {row[1] for row in connection.execute("PRAGMA table_info(p_audit_run)")}
                self.assertIn("idempotency_key", columns)
                issue_columns = {row[1] for row in connection.execute("PRAGMA table_info(p_audit_run_issue)")}
                self.assertNotIn("line_no", issue_columns)
                indexes = {row[1] for row in connection.execute("PRAGMA index_list(p_audit_run)")}
                self.assertIn("ux_audit_tasks_idempotency_key", indexes)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
