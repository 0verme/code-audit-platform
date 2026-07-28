import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.profiles import DatabaseProfile  # noqa: E402
from app.db.schema import RUNTIME_TABLES, initialize_schema  # noqa: E402
from app.db.sql_runner import SQLRunner  # noqa: E402
from app.db.tables import qualified_table_name, render_table_tokens  # noqa: E402
from scripts.migrate_sqlite_to_profile import SQLiteToProfileMigrator  # noqa: E402


def sqlite_profile(name: str, path: Path) -> DatabaseProfile:
    return DatabaseProfile(name, "sqlite", {"type": "sqlite", "path": str(path), "database": str(path)})


def seed_source(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(
            """
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_key TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                workflow TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE audit_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                source_ref TEXT NOT NULL DEFAULT '',
                workflow TEXT NOT NULL,
                status TEXT NOT NULL,
                revision TEXT NOT NULL,
                author TEXT NOT NULL,
                operator_user TEXT NOT NULL DEFAULT '',
                client_ip TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                duration TEXT NOT NULL,
                ai_enabled INTEGER NOT NULL DEFAULT 0,
                debug_enabled INTEGER NOT NULL DEFAULT 0,
                progress INTEGER NOT NULL DEFAULT 0,
                step TEXT NOT NULL DEFAULT '',
                finished_at TEXT,
                error TEXT,
                logs_json TEXT NOT NULL DEFAULT '[]',
                source_type TEXT NOT NULL DEFAULT 'svn'
            );
            CREATE TABLE task_reports (
                task_id INTEGER PRIMARY KEY,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                file_name TEXT NOT NULL,
                line_no INTEGER NOT NULL,
                rule_name TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            );
            CREATE TABLE fine_report_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                report_type TEXT NOT NULL,
                change_type TEXT NOT NULL,
                connection_name TEXT NOT NULL,
                focus TEXT NOT NULL,
                dataset_sql TEXT NOT NULL,
                dataset_rows TEXT NOT NULL,
                issues_json TEXT NOT NULL,
                ref_tables_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO projects (id, name, project_key, repo_path, workflow, description) VALUES (?, ?, ?, ?, ?, ?)",
            (1, "Demo", "demo", "https://example.com/repo.git", "hcyt", "demo"),
        )
        connection.execute(
            """
            INSERT INTO audit_tasks (
                id, repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
                started_at, duration, logs_json, source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "https://example.com/repo.git",
                "https://example.com/repo.git",
                "hcyt",
                "pass",
                "-",
                "tester",
                "tester",
                "127.0.0.1",
                "2026-07-06 00:00:00",
                "1s",
                json.dumps([{"msg": "中文\nline"}], ensure_ascii=False),
                "git",
            ),
        )
        connection.execute(
            "INSERT INTO task_reports (task_id, report_json, created_at) VALUES (?, ?, ?)",
            (1, json.dumps({"text": "中文\nline"}, ensure_ascii=False), "2026-07-06 00:00:01"),
        )
        connection.execute(
            """
            INSERT INTO audit_results (id, task_id, category, file_name, line_no, rule_name, level, message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "dws", "demo.sql", 1, "rule", "err", "message"),
        )
        connection.execute(
            """
            INSERT INTO fine_report_items (
                id, title, file_path, report_type, change_type, connection_name,
                focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "Report",
                "fine/report.cpt",
                "cpt",
                "M",
                "placeholder",
                "focus",
                "SELECT 1",
                "1",
                json.dumps([{"msg": "中文\nline"}], ensure_ascii=False),
                json.dumps([{"name": "DWS.TABLE"}], ensure_ascii=False),
            ),
        )


class FakeRunner:
    def __init__(self):
        self.rows = {table: {} for table in RUNTIME_TABLES}
        self.executed = []
        self.profile = DatabaseProfile(
            "local_pg",
            "postgresql",
            {
                "type": "postgresql",
                "host": "127.0.0.1",
                "port": 5432,
                "database": "code_audit",
                "username": "tester",
                "password": "secret",
                "schema": "dwp",
                "table_prefix": "p_audit_",
            },
        )

    def query_one(self, sql, params=()):
        sql = render_table_tokens(sql, self.profile)
        if sql.startswith("SELECT COUNT(*) AS count FROM "):
            table = next(name for name in RUNTIME_TABLES if qualified_table_name(name, self.profile) == sql.rsplit(" ", 1)[-1])
            return {"count": len(self.rows[table])}
        if " WHERE " in sql:
            physical_name = sql.split(" FROM ", 1)[1].split(" WHERE ", 1)[0]
            table = next(name for name in RUNTIME_TABLES if qualified_table_name(name, self.profile) == physical_name)
            return self.rows[table].get(params[0])
        raise AssertionError(f"unexpected query: {sql}")

    def execute(self, sql, params=()):
        sql = render_table_tokens(sql, self.profile)
        self.executed.append((sql, params))
        physical_name = sql.split(" INTO ", 1)[1].split(" ", 1)[0]
        table = next(name for name in RUNTIME_TABLES if qualified_table_name(name, self.profile) == physical_name)
        pk = "task_id" if table == "task_reports" else "id"
        columns = [column.strip() for column in sql.split("(", 1)[1].split(")", 1)[0].split(",")]
        row = dict(zip(columns, params))
        self.rows[table][row[pk]] = row


class MigrationScriptTests(unittest.TestCase):
    def test_dry_run_does_not_write_target(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            source = Path(tmp) / "source.db"
            seed_source(source)
            runner = FakeRunner()
            results = SQLiteToProfileMigrator(source, "local_pg", runner=runner, dry_run=True).migrate()
        self.assertTrue(all(result.inserted == 1 for result in results))
        self.assertEqual(runner.executed, [])

    def test_mock_target_migration_is_idempotent(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            source = Path(tmp) / "source.db"
            seed_source(source)
            runner = FakeRunner()
            first = SQLiteToProfileMigrator(source, "local_pg", runner=runner).migrate()
            second = SQLiteToProfileMigrator(source, "local_pg", runner=runner).migrate()
        self.assertTrue(all(result.inserted == 1 for result in first))
        self.assertTrue(all(result.inserted == 0 and result.skipped == 1 for result in second))
        self.assertNotIn("line_no", runner.rows["audit_results"][1])

    def test_sqlite_target_preserves_json_text(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            source = Path(tmp) / "source.db"
            target = Path(tmp) / "target.db"
            seed_source(source)
            profile = sqlite_profile("target", target)
            initialize_schema(profile)
            runner = SQLRunner(profile)
            SQLiteToProfileMigrator(source, "target", runner=runner).migrate()
            with closing(sqlite3.connect(target)) as connection:
                report_json = connection.execute(
                    f"SELECT report_json FROM {qualified_table_name('task_reports', profile)} WHERE task_id = 1"
                ).fetchone()[0]
                audit_result_columns = {
                    row[1]
                    for row in connection.execute(
                        f"PRAGMA table_info({qualified_table_name('audit_results', profile)})"
                    )
                }
        self.assertEqual(json.loads(report_json), {"text": "中文\nline"})
        self.assertNotIn("line_no", audit_result_columns)

    def test_missing_source_has_friendly_error(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            source = Path(tmp) / "missing.db"
            with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
                SQLiteToProfileMigrator(source, "local_pg", runner=FakeRunner()).migrate()


if __name__ == "__main__":
    unittest.main()
