import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database  # noqa: E402
from database import execute_insert, upsert_task_report  # noqa: E402


class DatabaseCompatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.old_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "app.db"
        self.config_path = Path(self.tmp.name) / "database.yaml"
        self.config_path.write_text(
            f"""
default_profile: sqlite
profiles:
  sqlite:
    type: sqlite
    path: {database.DB_PATH.as_posix()}
""",
            encoding="utf-8",
        )
        self.env_patcher = patch.dict(
            "os.environ",
            {
                "CODE_AUDIT_DB_CONFIG_PATH": str(self.config_path),
                "CODE_AUDIT_DB_PROFILE": "sqlite",
            },
            clear=False,
        )
        self.env_patcher.start()
        database.init_db()

    def tearDown(self):
        self.env_patcher.stop()
        database.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def test_sqlite_profile_creates_project(self):
        project_id = execute_insert(
            """
            INSERT INTO projects (name, project_key, repo_path, workflow, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Demo", "demo", "https://example.com/repo.git", "hcyt", "Demo project"),
        )
        self.assertGreater(project_id, 0)

    def test_sqlite_profile_creates_audit_task_and_returns_id(self):
        task_id = self._create_task()
        self.assertGreater(task_id, 0)

    def test_sqlite_profile_writes_task_report(self):
        task_id = self._create_task()
        report = {"task": {"id": task_id}, "items": ["中文", "line\nbreak"]}
        upsert_task_report(task_id, json.dumps(report, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        with database.get_connection() as connection:
            row = connection.execute("SELECT report_json FROM task_reports WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(json.loads(row["report_json"]), report)

    def test_sqlite_profile_writes_audit_results(self):
        task_id = self._create_task()
        with database.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_results (task_id, category, file_name, line_no, rule_name, level, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, "dws", "demo.sql", 1, "rule", "err", "message"),
            )
        with database.get_connection() as connection:
            row = connection.execute("SELECT category, file_name FROM audit_results WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(dict(row), {"category": "dws", "file_name": "demo.sql"})

    def test_sqlite_profile_queries_recent_audit_list(self):
        task_id = self._create_task()
        with database.get_connection() as connection:
            rows = connection.execute("SELECT id, status, logs_json FROM audit_tasks ORDER BY id DESC").fetchall()
        self.assertEqual(rows[0]["id"], task_id)
        self.assertEqual(rows[0]["status"], "running")

    def _create_task(self) -> int:
        return execute_insert(
            """
            INSERT INTO audit_tasks (
                repo, source_ref, workflow, status, revision, author, operator_user,
                client_ip, started_at, duration
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "https://example.com/repo.git",
                "https://example.com/repo.git",
                "hcyt",
                "running",
                "-",
                "tester",
                "tester",
                "127.0.0.1",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "0s",
            ),
        )


if __name__ == "__main__":
    unittest.main()
