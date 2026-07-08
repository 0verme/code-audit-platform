import importlib
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
import engine  # noqa: E402


class LocalAuditTaskTests(unittest.TestCase):
    def test_create_audit_task_accepts_local_source(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                app_module = importlib.import_module("app")
                captured = {}

                def fake_start_task(task_id, repo, workflow, ai_enabled=False, debug_enabled=False, author="local-user", source_type="svn"):
                    captured.update(
                        task_id=task_id,
                        repo=repo,
                        workflow=workflow,
                        ai_enabled=ai_enabled,
                        debug_enabled=debug_enabled,
                        author=author,
                        source_type=source_type,
                    )
                    return None

                with patch.object(app_module.engine, "start_task", fake_start_task):
                    response = app_module.app.test_client().post(
                        "/api/audit-tasks",
                        json={
                            "repo": "C:\\path\\to\\local-hcyt-workspace",
                            "sourceType": "local",
                            "workflow": "hcyt",
                            "debug_enabled": True,
                        },
                    )

                self.assertEqual(response.status_code, 201)
                body = response.get_json()
                self.assertEqual(body["sourceType"], "local")
                self.assertEqual(body["sourceRef"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(captured["source_type"], "local")
                self.assertEqual(captured["workflow"], "hcyt")

                with database.get_connection() as connection:
                    row = connection.execute(
                        "SELECT source_type, source_ref, operator_user, client_ip FROM {{table:audit_tasks}} WHERE id = ?",
                        (body["id"],),
                    ).fetchone()
                self.assertEqual(row["source_type"], "local")
                self.assertEqual(row["source_ref"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(row["operator_user"], "local-user")
                self.assertTrue(row["client_ip"])
            finally:
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_task_keeps_svn_default(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            body = {}
            try:
                app_module = importlib.import_module("app")
                captured = {}

                with patch.object(app_module.engine, "start_task", lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs)):
                    response = app_module.app.test_client().post(
                        "/api/audit-tasks",
                        json={"repo": "svn://example.com/repos/branches/demo-hcyt", "workflow": "hcyt"},
                    )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.get_json()["sourceType"], "svn")
                self.assertEqual(captured["args"][6], "svn")
            finally:
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_task_accepts_git_source_and_infers_type(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                app_module = importlib.import_module("app")
                with patch.object(app_module.engine, "start_task", lambda *args, **kwargs: None):
                    response = app_module.app.test_client().post(
                        "/api/audit-tasks",
                        json={"sourceRef": "git@gitlab.example.com:team/repo.git", "workflow": "hcyt"},
                    )

                self.assertEqual(response.status_code, 201)
                body = response.get_json()
                self.assertEqual(body["sourceType"], "git")
                self.assertEqual(body["sourceRef"], "git@gitlab.example.com:team/repo.git")
            finally:
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_run_alias_returns_run_id_and_partial_status(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                app_module = importlib.import_module("app")

                def fake_start_task(task_id, _repo, workflow, *_args, **_kwargs):
                    state = app_module.engine.create_audit_run_state(task_id, workflow)
                    state.mark_running()
                    state.set_section("changes", [{"path": "demo.sql"}])
                    state.get_task("source_load").mark_success(summary={"files": 1})

                with patch.object(app_module.engine, "start_task", fake_start_task):
                    response = app_module.app.test_client().post(
                        "/api/audit-runs",
                        json={"repo": "svn://example.com/repos/branches/demo-hcyt", "workflow": "hcyt"},
                    )

                self.assertEqual(response.status_code, 201)
                body = response.get_json()
                self.assertEqual(body["run_id"], body["id"])
                self.assertEqual(body["runId"], body["id"])

                status_response = app_module.app.test_client().get(f"/api/audit-runs/{body['run_id']}/status")
                self.assertEqual(status_response.status_code, 200)
                status = status_response.get_json()
                self.assertEqual(status["runId"], body["id"])
                self.assertEqual(status["taskStatus"], "running")
                self.assertEqual(status["tasks"]["source_load"]["status"], "success")

                partial_response = app_module.app.test_client().get(
                    f"/api/audit-runs/{body['run_id']}/partial-result"
                )
                self.assertEqual(partial_response.status_code, 200)
                partial = partial_response.get_json()
                self.assertFalse(partial["finalReportReady"])
                self.assertEqual(partial["partialReport"]["changes"], [{"path": "demo.sql"}])
            finally:
                if body.get("id"):
                    app_module.engine._run_states.pop(body["id"], None)
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_audit_run_status_falls_back_to_database_report(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                app_module = importlib.import_module("app")
                task_id = database.execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, source_ref, workflow, status, revision, author, started_at, duration, progress
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "svn://example.com/repos/branches/demo-hcyt",
                        "svn://example.com/repos/branches/demo-hcyt",
                        "hcyt",
                        "pass",
                        "r1",
                        "tester",
                        datetime.now().isoformat(),
                        "2s",
                        100,
                    ),
                )
                database.upsert_task_report(
                    task_id,
                    json.dumps({"task": {"status": "pass"}, "changes": [{"path": "demo.sql"}]}),
                    datetime.now().isoformat(),
                )

                response = app_module.app.test_client().get(f"/api/audit-runs/{task_id}/partial-result")
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                self.assertTrue(body["finalReportReady"])
                self.assertEqual(body["status"], "success")
                self.assertEqual(body["report"]["changes"], [{"path": "demo.sql"}])
                self.assertEqual(body["partialReport"]["finalReport"]["task"]["status"], "pass")
            finally:
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_task_run_marks_audit_run_state_running_immediately(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            try:
                database.init_db()
                task_id = database.execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, workflow, status, revision, author, started_at, duration, progress
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("C:\\path\\to\\local-hcyt-workspace", "hcyt", "running", "-", "tester", datetime.now().isoformat(), "0s", 0),
                )

                run = engine.TaskRun(task_id, "C:\\path\\to\\local-hcyt-workspace", "hcyt", source_type="local")

                self.assertEqual(run.run_state.status.value, "running")
                self.assertEqual(engine.get_audit_run_status(task_id)["status"], "running")
            finally:
                engine._run_states.pop(task_id, None)
                database.DB_PATH = old_db_path

    def test_audit_run_partial_result_preserves_final_report_compatibility_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                app_module = importlib.import_module("app")
                task_id = database.execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, source_ref, workflow, status, revision, author, started_at, duration, progress
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "svn://example.com/repos/branches/demo-hcyt",
                        "svn://example.com/repos/branches/demo-hcyt",
                        "hcyt",
                        "fail",
                        "r2",
                        "tester",
                        datetime.now().isoformat(),
                        "3s",
                        100,
                    ),
                )
                final_report = {
                    "task": {"status": "fail", "errors": 1, "warnings": 0, "conflicts": 0},
                    "changes": [{"path": "demo.sql"}],
                    "dws": [{"level": "err", "file": "demo.sql", "rule": "rule", "msg": "bad"}],
                    "assetIssues": [{"issueType": "missing-root", "objectName": "DM.TABLE_A"}],
                    "unifiedAssetIssues": [{"rule_code": "missing-root", "object_name": "DM.TABLE_A"}],
                    "lineageSummary": {"resultTables": ["DM.TABLE_A"], "jobs": [], "recvPlans": [], "sysNames": [], "outfiles": [], "warnings": [], "stats": {}},
                }
                database.upsert_task_report(task_id, json.dumps(final_report), datetime.now().isoformat())

                response = app_module.app.test_client().get(f"/api/audit-runs/{task_id}/partial-result")
                self.assertEqual(response.status_code, 200)
                body = response.get_json()

                self.assertTrue(body["finalReportReady"])
                self.assertEqual(body["status"], "success")
                self.assertEqual(body["taskStatus"], "fail")
                self.assertEqual(body["report"], final_report)
                self.assertEqual(body["partialReport"]["finalReport"], final_report)
                self.assertEqual(body["report"]["assetIssues"], final_report["assetIssues"])
                self.assertEqual(body["report"]["unifiedAssetIssues"], final_report["unifiedAssetIssues"])
                self.assertEqual(body["report"]["lineageSummary"], final_report["lineageSummary"])
            finally:
                database.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_report_meta_contains_local_source_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = database.DB_PATH
            database.DB_PATH = db_path
            try:
                database.init_db()
                task_id = database.execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, workflow, status, revision, author, started_at, duration, source_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("C:\\path\\to\\local-hcyt-workspace", "hcyt", "running", "-", "tester", datetime.now().isoformat(), "0s", "local"),
                )

                run = engine.TaskRun(task_id, "C:\\path\\to\\local-hcyt-workspace", "hcyt", source_type="local")
                workspace = {
                    "source_type": "local",
                    "workspace_root": "C:\\path\\to\\local-hcyt-workspace",
                    "create_revision": "",
                }
                report = {"task": run.build_task_meta(workspace, "pass", {"changedFiles": 1}), "changes": [{"path": "demo.sql"}]}
                report["sourceType"] = workspace["source_type"]
                report["workspaceRoot"] = workspace["workspace_root"]
                run.finish("pass", report=report)

                with database.get_connection() as connection:
                    row = connection.execute("SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?", (task_id,)).fetchone()
                saved = json.loads(row["report_json"])
                self.assertEqual(saved["sourceType"], "local")
                self.assertEqual(saved["workspaceRoot"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(saved["task"]["sourceType"], "local")
                self.assertEqual(saved["task"]["workspaceRoot"], "C:\\path\\to\\local-hcyt-workspace")
            finally:
                database.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
