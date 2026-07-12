import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.checks.workspace_service import load_local_workspace, validate_local_workspace
from audit.source_resolver import LocalSourceDisabledError, resolve_workspace
from runtime_security import RuntimeSecuritySettings, get_runtime_security_settings


class RuntimeSecurityTests(unittest.TestCase):
    def test_defaults_are_safe_and_boolean_values_are_explicit(self):
        defaults = get_runtime_security_settings({})
        self.assertFalse(defaults.local_source_enabled)
        self.assertFalse(defaults.debug)
        self.assertEqual(defaults.host, "127.0.0.1")
        self.assertEqual(defaults.port, 5088)
        self.assertEqual(defaults.cors_origins, ("http://localhost:5173", "http://127.0.0.1:5173"))
        self.assertTrue(get_runtime_security_settings({"AUDIT_LOCAL_SOURCE_ENABLED": "yes"}).local_source_enabled)
        self.assertFalse(get_runtime_security_settings({"AUDIT_DEBUG": "off"}).debug)
        with self.assertRaises(ValueError):
            get_runtime_security_settings({"AUDIT_DEBUG": "maybe"})

    def test_lists_parse_json_and_reject_cors_wildcard(self):
        settings = get_runtime_security_settings({
            "AUDIT_LOCAL_SOURCE_ROOTS": '["/tmp/one", "/tmp/two"]',
            "AUDIT_CORS_ORIGINS": 'http://localhost:5173, http://127.0.0.1:5173',
        })
        self.assertEqual(settings.local_source_roots, ("/tmp/one", "/tmp/two"))
        self.assertEqual(settings.cors_origins, ("http://localhost:5173", "http://127.0.0.1:5173"))
        with self.assertRaises(ValueError):
            get_runtime_security_settings({"AUDIT_CORS_ORIGINS": "*"})

    def test_resolver_cannot_bypass_disabled_local_source(self):
        loader = Mock()
        with self.assertRaises(LocalSourceDisabledError):
            resolve_workspace("/tmp/workspace", "hcyt", "local", svn_loader=Mock(), local_loader=loader)
        loader.assert_not_called()

    def test_workspace_allowlist_and_symlink_boundary(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp) / "allowed"
            root.mkdir()
            nested = root / "nested"
            nested.mkdir()
            (nested / "safe.sql").write_text("select 1", encoding="utf-8")
            (Path(outside) / "secret.sql").write_text("secret", encoding="utf-8")
            settings = RuntimeSecuritySettings(local_source_enabled=True, local_source_roots=(str(root),))
            self.assertEqual(validate_local_workspace(str(root), settings), root.resolve())
            self.assertEqual(validate_local_workspace(str(nested), settings), nested.resolve())
            with self.assertRaises(PermissionError):
                validate_local_workspace(str(Path(tmp)), settings)
            with self.assertRaises(FileNotFoundError):
                validate_local_workspace(str(Path(tmp) / "allowed-copy"), settings)
            with self.assertRaises(NotADirectoryError):
                validate_local_workspace(str(nested / "safe.sql"), settings)
            link = root / "outside-link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks are unavailable on this platform")
            info = load_local_workspace(str(root), security_settings=settings)
            self.assertEqual(info["branch_changed_files"], ["nested/safe.sql"])

    def test_api_rejects_disabled_local_before_task_creation(self):
        with patch.dict(os.environ, {"AUDIT_LOCAL_SOURCE_ENABLED": "false"}, clear=False):
            sys.modules.pop("app", None)
            app_module = importlib.import_module("app")
            start_task = Mock()
            with patch.object(app_module.audit_engine, "start_task", start_task):
                response = app_module.app.test_client().post("/api/audit-tasks", json={"sourceType": "local", "sourceRef": "/tmp/workspace"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json()["errorCode"], "local_source_disabled")
            start_task.assert_not_called()
            sys.modules.pop("app", None)

    def test_cors_only_allows_configured_origins(self):
        with patch.dict(os.environ, {"AUDIT_CORS_ORIGINS": "http://localhost:5173"}, clear=False):
            sys.modules.pop("app", None)
            app_module = importlib.import_module("app")
            client = app_module.app.test_client()
            self.assertEqual(client.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")
            self.assertIsNone(client.get("/api/health", headers={"Origin": "https://untrusted.example"}).headers.get("Access-Control-Allow-Origin"))
            sys.modules.pop("app", None)


if __name__ == "__main__":
    unittest.main()
