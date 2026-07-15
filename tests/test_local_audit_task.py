import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
from app.modules.audit.checks.svn_service import SvnCliNotFoundError  # noqa: E402
from app.db import connection as db_connection  # noqa: E402
from app.db.runtime_store import upsert_task_report  # noqa: E402
from app.db.schema import init_db  # noqa: E402
from app.db.sql_runner import execute_insert  # noqa: E402


class LocalAuditTaskTests(unittest.TestCase):
    def setUp(self):
        self._security_env = patch.dict(os.environ, {"AUDIT_LOCAL_SOURCE_ENABLED": "true"}, clear=False)
        self._security_env.start()

    def tearDown(self):
        self._security_env.stop()

    def _insert_task(self, repo, workflow="hcyt", source_type="svn"):
        return execute_insert(
            """
            INSERT INTO {{table:audit_tasks}} (
                repo, workflow, status, revision, author, started_at, duration, source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo,
                workflow,
                "running",
                "-",
                "tester",
                datetime.now().isoformat(),
                "0s",
                source_type,
            ),
        )

    def _load_saved_report(self, task_id):
        with db_connection.get_connection() as connection:
            row = connection.execute(
                "SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return json.loads(row["report_json"])

    def _load_task_row(self, task_id):
        with db_connection.get_connection() as connection:
            return connection.execute(
                "SELECT status, error, progress, step FROM {{table:audit_tasks}} WHERE id = ?",
                (task_id,),
            ).fetchone()

    def test_create_audit_task_accepts_local_source(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                init_db()
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

                with patch.object(audit_engine, "start_task", fake_start_task), patch("app.services.audit_task_service.validate_local_workspace"):
                    response = app_module.create_app().test_client().post(
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

                with db_connection.get_connection() as connection:
                    row = connection.execute(
                        "SELECT source_type, source_ref, operator_user, client_ip FROM {{table:audit_tasks}} WHERE id = ?",
                        (body["id"],),
                    ).fetchone()
                self.assertEqual(row["source_type"], "local")
                self.assertEqual(row["source_ref"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(row["operator_user"], "local-user")
                self.assertTrue(row["client_ip"])

                with patch("app.services.audit_task_service.validate_local_workspace"):
                    for workflow in ("nups", "fine-report"):
                        response = app_module.create_app().test_client().post(
                            "/api/audit-tasks",
                            json={
                                "repo": f"C:\\path\\to\\local-{workflow}-workspace",
                                "sourceType": "local",
                                "workflow": workflow,
                            },
                        )
                        self.assertEqual(response.status_code, 201)
                        self.assertEqual(response.get_json()["workflow"], workflow)
            finally:
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_task_keeps_svn_default(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            body = {}
            try:
                init_db()
                app_module = importlib.import_module("app")
                captured = {}

                with patch.object(audit_engine, "start_task", lambda *args, **kwargs: captured.update(args=args, kwargs=kwargs)):
                    response = app_module.create_app().test_client().post(
                        "/api/audit-tasks",
                        json={"repo": "svn://example.com/repos/branches/demo-hcyt", "workflow": "hcyt"},
                    )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.get_json()["sourceType"], "svn")
                self.assertEqual(captured["args"][6], "svn")
            finally:
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_task_rejects_git_sources_before_creating_or_starting_tasks(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                init_db()
                app_module = importlib.import_module("app")
                start_task = Mock()
                with patch.object(audit_engine, "start_task", start_task):
                    for payload in (
                        {"sourceRef": "svn://example.com/repos/branches/demo-hcyt", "sourceType": "git", "workflow": "hcyt"},
                        {"sourceRef": "svn://example.com/repos/branches/demo-hcyt", "source_type": "git", "workflow": "hcyt"},
                        {"sourceRef": "git@gitlab.example.com:team/repo.git", "workflow": "hcyt"},
                    ):
                        response = app_module.create_app().test_client().post("/api/audit-tasks", json=payload)

                        self.assertEqual(response.status_code, 400)
                        body = response.get_json()
                        self.assertEqual(body["errorCode"], "unsupported_audit_source")
                        self.assertEqual(body["error"], "Git audit source is not supported in the current version.")

                start_task.assert_not_called()
                with db_connection.get_connection() as connection:
                    task_count = connection.execute(
                        "SELECT COUNT(*) AS count FROM {{table:audit_tasks}}",
                    ).fetchone()["count"]
                self.assertEqual(task_count, 0)
            finally:
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_create_audit_run_alias_returns_run_id_and_partial_status(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                init_db()
                app_module = importlib.import_module("app")

                def fake_start_task(task_id, _repo, workflow, *_args, **_kwargs):
                    state = audit_engine.create_audit_run_state(task_id, workflow)
                    state.mark_running()
                    state.set_section("changes", [{"path": "demo.sql"}])
                    state.get_task("source_load").mark_success(summary={"files": 1})

                with patch.object(audit_engine, "start_task", fake_start_task):
                    client = app_module.create_app().test_client()
                    response = client.post(
                        "/api/audit-runs",
                        json={"repo": "svn://example.com/repos/branches/demo-hcyt", "workflow": "hcyt"},
                    )

                self.assertEqual(response.status_code, 201)
                body = response.get_json()
                self.assertEqual(body["run_id"], body["id"])
                self.assertEqual(body["runId"], body["id"])

                status_response = client.get(f"/api/audit-runs/{body['run_id']}/status")
                self.assertEqual(status_response.status_code, 200)
                status = status_response.get_json()
                self.assertEqual(status["runId"], body["id"])
                self.assertEqual(status["taskStatus"], "running")
                self.assertEqual(status["tasks"]["source_load"]["status"], "success")

                partial_response = client.get(
                    f"/api/audit-runs/{body['run_id']}/partial-result"
                )
                self.assertEqual(partial_response.status_code, 200)
                partial = partial_response.get_json()
                self.assertFalse(partial["finalReportReady"])
                self.assertEqual(partial["partialReport"]["changes"], [{"path": "demo.sql"}])
            finally:
                if body.get("id"):
                    audit_engine._run_states.pop(body["id"], None)
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_audit_run_status_falls_back_to_database_report(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                init_db()
                app_module = importlib.import_module("app")
                task_id = execute_insert(
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
                upsert_task_report(
                    task_id,
                    json.dumps({"task": {"status": "pass"}, "changes": [{"path": "demo.sql"}]}),
                    datetime.now().isoformat(),
                )

                response = app_module.create_app().test_client().get(f"/api/audit-runs/{task_id}/partial-result")
                self.assertEqual(response.status_code, 200)
                body = response.get_json()
                self.assertTrue(body["finalReportReady"])
                self.assertEqual(body["status"], "success")
                self.assertEqual(body["report"]["changes"], [{"path": "demo.sql"}])
                self.assertEqual(body["partialReport"]["finalReport"]["task"]["status"], "pass")
            finally:
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_task_run_marks_audit_run_state_running_immediately(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            try:
                init_db()
                task_id = execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, workflow, status, revision, author, started_at, duration, progress
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("C:\\path\\to\\local-hcyt-workspace", "hcyt", "running", "-", "tester", datetime.now().isoformat(), "0s", 0),
                )

                run = audit_engine.TaskRun(task_id, "C:\\path\\to\\local-hcyt-workspace", "hcyt", source_type="local")

                self.assertEqual(run.run_state.status.value, "running")
                self.assertEqual(audit_engine.get_audit_run_status(task_id)["status"], "running")
            finally:
                audit_engine._run_states.pop(task_id, None)
                db_connection.DB_PATH = old_db_path

    def test_audit_run_partial_result_preserves_final_report_compatibility_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            sys.modules.pop("app", None)
            try:
                init_db()
                app_module = importlib.import_module("app")
                task_id = execute_insert(
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
                upsert_task_report(task_id, json.dumps(final_report), datetime.now().isoformat())

                response = app_module.create_app().test_client().get(f"/api/audit-runs/{task_id}/partial-result")
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
                db_connection.DB_PATH = old_db_path
                sys.modules.pop("app", None)

    def test_report_meta_contains_local_source_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            try:
                init_db()
                task_id = execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, workflow, status, revision, author, started_at, duration, source_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("C:\\path\\to\\local-hcyt-workspace", "hcyt", "running", "-", "tester", datetime.now().isoformat(), "0s", "local"),
                )

                run = audit_engine.TaskRun(task_id, "C:\\path\\to\\local-hcyt-workspace", "hcyt", source_type="local")
                workspace = {
                    "source_type": "local",
                    "workspace_root": "C:\\path\\to\\local-hcyt-workspace",
                    "create_revision": "",
                }
                report = {"task": run.build_task_meta(workspace, "pass", {"changedFiles": 1}), "changes": [{"path": "demo.sql"}]}
                report["sourceType"] = workspace["source_type"]
                report["workspaceRoot"] = workspace["workspace_root"]
                run.finish("pass", report=report)

                with db_connection.get_connection() as connection:
                    row = connection.execute("SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?", (task_id,)).fetchone()
                saved = json.loads(row["report_json"])
                self.assertEqual(saved["sourceType"], "local")
                self.assertEqual(saved["workspaceRoot"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(saved["task"]["sourceType"], "local")
                self.assertEqual(saved["task"]["workspaceRoot"], "C:\\path\\to\\local-hcyt-workspace")
            finally:
                db_connection.DB_PATH = old_db_path

    def test_task_run_local_source_preserves_final_report_source_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            previous_mods = audit_engine._mods
            try:
                init_db()
                task_id = execute_insert(
                    """
                    INSERT INTO {{table:audit_tasks}} (
                        repo, workflow, status, revision, author, started_at, duration, source_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "C:\\path\\to\\local-hcyt-workspace",
                        "hcyt",
                        "running",
                        "-",
                        "tester",
                        datetime.now().isoformat(),
                        "0s",
                        "local",
                    ),
                )

                audit_engine._mods = types.SimpleNamespace(
                    load_local_workspace=lambda repo, workflow: {
                        "source_type": "local",
                        "workspace_root": repo,
                        "exported_paths": ["demo.sql"],
                    },
                    svn_main=lambda *_args, **_kwargs: None,
                )
                run = audit_engine.TaskRun(task_id, "C:\\path\\to\\local-hcyt-workspace", "hcyt", source_type="local")
                run.update = lambda *args, **kwargs: None

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    with patch.object(audit_engine, "run_workflow", return_value={"task": {"status": "pass"}}):
                        run.run()

                with db_connection.get_connection() as connection:
                    row = connection.execute(
                        "SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?",
                        (task_id,),
                    ).fetchone()
                saved = json.loads(row["report_json"])

                self.assertEqual(saved["sourceType"], "local")
                self.assertEqual(saved["sourceRef"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(saved["workspaceRoot"], "C:\\path\\to\\local-hcyt-workspace")
                self.assertEqual(saved["logs"], run.logs)
                self.assertTrue(saved["logs"])
            finally:
                audit_engine._mods = previous_mods
                audit_engine._run_states.pop(task_id, None)
                db_connection.DB_PATH = old_db_path

    def test_task_run_svn_source_normalizes_report_source_fields(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            previous_mods = audit_engine._mods
            try:
                init_db()
                repo = "svn://example.com/repos/branches/demo-hcyt"
                task_id = self._insert_task(repo)
                audit_engine._mods = types.SimpleNamespace(
                    svn_main=lambda *_args, **_kwargs: {
                        "create_revision": "123",
                        "exported_paths": ["demo.sql"],
                    }
                )
                run = audit_engine.TaskRun(task_id, repo, "hcyt", source_type="svn")
                run.update = lambda *args, **kwargs: None

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    with patch.object(audit_engine, "run_workflow", return_value={"task": {"status": "pass"}}):
                        run.run()

                saved = self._load_saved_report(task_id)
                row = self._load_task_row(task_id)
                self.assertEqual(saved["sourceType"], "svn")
                self.assertEqual(saved["sourceRef"], repo)
                self.assertEqual(saved["workspaceRoot"], "")
                self.assertEqual(saved["logs"], run.logs)
                self.assertEqual(saved["task"]["status"], "pass")
                self.assertEqual(row["status"], "pass")
                self.assertEqual(row["progress"], 100)
                self.assertEqual(row["step"], "completed")
            finally:
                audit_engine._mods = previous_mods
                audit_engine._run_states.pop(task_id, None)
                db_connection.DB_PATH = old_db_path

    def test_task_run_local_source_uses_workspace_loader_contract(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            previous_mods = audit_engine._mods
            try:
                init_db()
                repo = "C:\\path\\to\\local-hcyt-workspace"
                task_id = self._insert_task(repo, source_type="local")
                load_local_workspace = Mock(
                    return_value={
                        "source_type": "local",
                        "workspace_root": repo,
                        "exported_paths": ["demo.sql"],
                    }
                )
                svn_main = Mock()
                audit_engine._mods = types.SimpleNamespace(
                    load_local_workspace=load_local_workspace,
                    svn_main=svn_main,
                )
                run = audit_engine.TaskRun(task_id, repo, "hcyt", source_type="local")
                run.update = lambda *args, **kwargs: None

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    with patch.object(audit_engine, "run_workflow", return_value={"task": {"status": "pass"}}):
                        run.run()

                saved = self._load_saved_report(task_id)
                load_local_workspace.assert_called_once_with(repo, "hcyt")
                svn_main.assert_not_called()
                self.assertEqual(saved["sourceType"], "local")
                self.assertEqual(saved["sourceRef"], repo)
                self.assertEqual(saved["workspaceRoot"], repo)
                self.assertEqual(saved["logs"], run.logs)
            finally:
                audit_engine._mods = previous_mods
                audit_engine._run_states.pop(task_id, None)
                db_connection.DB_PATH = old_db_path

    def test_task_run_svn_cli_hint_only_applies_to_svn_source(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            previous_mods = audit_engine._mods
            svn_task_id = None
            local_task_id = None
            try:
                init_db()
                svn_repo = "svn://example.com/repos/branches/demo-hcyt"
                svn_task_id = self._insert_task(svn_repo, source_type="svn")
                audit_engine._mods = types.SimpleNamespace(
                    svn_main=Mock(side_effect=SvnCliNotFoundError("svn missing"))
                )
                svn_run = audit_engine.TaskRun(svn_task_id, svn_repo, "hcyt", source_type="svn")
                svn_run.update = lambda *args, **kwargs: None

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    svn_run.run()

                svn_row = self._load_task_row(svn_task_id)
                self.assertIn("svn missing", svn_row["error"])
                self.assertIn("未找到 svn 命令行客户端，请安装 SVN 并加入 PATH", svn_row["error"])

                local_repo = "C:\\path\\to\\local-hcyt-workspace"
                local_task_id = self._insert_task(local_repo, source_type="local")
                audit_engine._mods = types.SimpleNamespace(
                    load_local_workspace=Mock(side_effect=FileNotFoundError("svn missing")),
                    svn_main=Mock(),
                )
                local_run = audit_engine.TaskRun(local_task_id, local_repo, "hcyt", source_type="local")
                local_run.update = lambda *args, **kwargs: None

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    local_run.run()

                local_row = self._load_task_row(local_task_id)
                self.assertIn("svn missing", local_row["error"])
                self.assertNotIn("未找到 svn 命令行客户端，请安装 SVN 并加入 PATH", local_row["error"])
            finally:
                audit_engine._mods = previous_mods
                audit_engine._run_states.pop(svn_task_id, None)
                audit_engine._run_states.pop(local_task_id, None)
                db_connection.DB_PATH = old_db_path

    def test_task_run_dispatches_to_matching_workflow_runner_only(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "app.db"
            old_db_path = db_connection.DB_PATH
            db_connection.DB_PATH = db_path
            previous_mods = audit_engine._mods
            try:
                init_db()
                audit_engine._mods = types.SimpleNamespace(
                    svn_main=lambda *_args, **_kwargs: {
                        "create_revision": "123",
                        "exported_paths": ["demo.sql"],
                    }
                )
                cases = (
                    ("svn://example.com/repos/branches/hcyt/demo", "run_hcyt"),
                    ("svn://example.com/repos/branches/nups/demo", "run_nups"),
                    ("svn://example.com/repos/branches/fine-report/demo", "run_fine"),
                )

                with patch.object(audit_engine, "_load_real_modules", lambda: None):
                    with patch("app.modules.audit.workflow_dispatcher.run_hcyt", return_value={"task": {"status": "pass"}}) as run_hcyt:
                        with patch("app.modules.audit.workflow_dispatcher.run_nups", return_value={"task": {"status": "pass"}}) as run_nups:
                            with patch("app.modules.audit.workflow_dispatcher.run_fine", return_value={"task": {"status": "pass"}}) as run_fine:
                                for repo, expected_runner in cases:
                                    task_id = self._insert_task(repo)
                                    run = audit_engine.TaskRun(task_id, repo, "hcyt", source_type="svn")
                                    run.update = lambda *args, **kwargs: None

                                    run.run()

                                    calls = {
                                        "run_hcyt": run_hcyt.call_count,
                                        "run_nups": run_nups.call_count,
                                        "run_fine": run_fine.call_count,
                                    }
                                    self.assertEqual(calls[expected_runner], 1, repo)
                                    for runner_name, count in calls.items():
                                        if runner_name != expected_runner:
                                            self.assertEqual(count, 0, repo)
                                    run_hcyt.reset_mock()
                                    run_nups.reset_mock()
                                    run_fine.reset_mock()
                                    audit_engine._run_states.pop(task_id, None)
            finally:
                audit_engine._mods = previous_mods
                db_connection.DB_PATH = old_db_path


if __name__ == "__main__":
    unittest.main()
