import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.connection import split_sql_statements  # noqa: E402
from app.db.profiles import DatabaseProfile  # noqa: E402
from app.db.tables import qualified_table_name, render_table_tokens  # noqa: E402
from app.migrations import MigrationRunner  # noqa: E402


MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def sqlite_profile(path: Path) -> DatabaseProfile:
    return DatabaseProfile(
        "migration_test",
        "sqlite",
        {"type": "sqlite", "path": str(path), "database": str(path), "table_prefix": ""},
    )


class RemoveAuditResultLineMigrationTests(unittest.TestCase):
    def test_full_sqlite_migration_chain_removes_line_number(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            path = Path(tmp) / "migration.db"
            connection = sqlite3.connect(path)
            try:
                runner = MigrationRunner(connection, "sqlite", MIGRATIONS_DIR, sqlite_profile(path))
                self.assertEqual(runner.apply(), ["0001", "0002", "0003", "0004"])
                table = qualified_table_name("audit_results", sqlite_profile(path))
                columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                indexes = {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}
                delete_plan = " ".join(
                    str(column)
                    for row in connection.execute(f"EXPLAIN QUERY PLAN DELETE FROM {table} WHERE task_id = 1")
                    for column in row
                )
                versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
            finally:
                connection.close()

        self.assertNotIn("line_no", columns)
        self.assertIn("ix_p_audit_run_issue_task_id", indexes)
        self.assertIn("ix_p_audit_run_issue_task_id", delete_plan)
        self.assertEqual(versions, ["0001", "0002", "0003", "0004"])

    def test_line_removal_migration_preserves_existing_findings(self):
        with closing(sqlite3.connect(":memory:")) as connection, connection:
            profile = DatabaseProfile("legacy", "sqlite", {"type": "sqlite"})
            table = qualified_table_name("audit_results", profile)
            connection.executescript(
                f"""
                CREATE TABLE {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    line_no INTEGER NOT NULL,
                    rule_name TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                INSERT INTO {table} (
                    task_id, category, file_name, line_no, rule_name, level, message
                ) VALUES (1, 'dws', 'demo.sql', 42, 'rule', 'warn', 'message');
                """
            )
            migration_sql = render_table_tokens(
                (MIGRATIONS_DIR / "sqlite" / "0003_remove_audit_result_line_number.sql").read_text(encoding="utf-8"),
                profile,
            )
            for statement in split_sql_statements(migration_sql):
                connection.execute(statement)

            row = connection.execute(
                f"SELECT id, task_id, category, file_name, rule_name, level, message FROM {table}"
            ).fetchone()
            columns = {item[1] for item in connection.execute(f"PRAGMA table_info({table})")}

        self.assertEqual(row, (1, 1, "dws", "demo.sql", "rule", "warn", "message"))
        self.assertNotIn("line_no", columns)


if __name__ == "__main__":
    unittest.main()
