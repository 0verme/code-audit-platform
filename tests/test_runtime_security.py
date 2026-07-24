import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.source.resolver import LocalSourceDisabledError, resolve_workspace  # noqa: E402
from app.modules.audit.source.workspace import load_local_workspace, validate_local_workspace  # noqa: E402
from app.settings import (  # noqa: E402
    LocalLLMSettings,
    RuntimeSecuritySettings,
    get_local_llm_settings,
    get_runtime_security_settings,
    load_backend_dotenv,
    resolve_local_roots,
)


class RuntimeSecurityTests(unittest.TestCase):
    def test_backend_dotenv_loads_and_process_environment_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                'AUDIT_LOCAL_SOURCE_ENABLED=true\n'
                'AUDIT_LOCAL_SOURCE_ROOTS=["C:\\\\audit\\\\one", "D:\\\\audit\\\\two"]\n'
                'AUDIT_PORT=5099\n',
                encoding="utf-8",
            )
            environ = {"AUDIT_PORT": "6000"}
            self.assertEqual(load_backend_dotenv(env_file, environ=environ), env_file)
            self.assertEqual(environ["AUDIT_LOCAL_SOURCE_ENABLED"], "true")
            self.assertEqual(environ["AUDIT_PORT"], "6000")
            settings = get_runtime_security_settings(environ)
            self.assertTrue(settings.local_source_enabled)
            self.assertEqual(settings.port, 6000)
            self.assertEqual(settings.local_source_roots, (r"C:\audit\one", r"D:\audit\two"))

    def test_windows_json_roots_resolve_as_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            settings = get_runtime_security_settings({"AUDIT_LOCAL_SOURCE_ROOTS": json.dumps([str(root)])})
            self.assertEqual(resolve_local_roots(settings), (root.resolve(),))

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

    def test_local_llm_settings_are_typed_and_normalised(self):
        settings = get_local_llm_settings({
            "LOCAL_LLM_BASE_URL": " http://localhost:8000/v1/// ",
            "LOCAL_LLM_MODEL": " local-model ",
            "LOCAL_LLM_API_KEY": " test-key ",
            "LOCAL_LLM_TIMEOUT_SECONDS": "12.5",
        })
        self.assertIsInstance(settings, LocalLLMSettings)
        self.assertTrue(settings.enabled)
        self.assertEqual(settings.base_url, "http://localhost:8000/v1")
        self.assertEqual(settings.model, "local-model")
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.timeout_seconds, 12.5)

    def test_local_llm_defaults_and_invalid_timeout(self):
        settings = get_local_llm_settings({})
        self.assertFalse(settings.enabled)
        self.assertEqual(settings.timeout_seconds, 30.0)
        for value in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "LOCAL_LLM_TIMEOUT_SECONDS"):
                get_local_llm_settings({"LOCAL_LLM_TIMEOUT_SECONDS": value})

    def test_resolver_cannot_bypass_disabled_local_source(self):
        loader = Mock()
        with self.assertRaises(LocalSourceDisabledError):
            resolve_workspace(
                "/tmp/workspace",
                "hcyt",
                "local",
                svn_loader=Mock(),
                local_loader=loader,
                security_settings=RuntimeSecuritySettings(local_source_enabled=False),
            )
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
            with patch("app.services.audit_task_service.audit_engine.start_task", start_task):
                response = app_module.create_app().test_client().post("/api/audit-tasks", json={"sourceType": "local", "sourceRef": "/tmp/workspace"})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.get_json()["errorCode"], "local_source_disabled")
            start_task.assert_not_called()
            sys.modules.pop("app", None)

    def test_cors_only_allows_configured_origins(self):
        with patch.dict(os.environ, {"AUDIT_CORS_ORIGINS": "http://localhost:5173"}, clear=False):
            sys.modules.pop("app", None)
            app_module = importlib.import_module("app")
            client = app_module.create_app().test_client()
            self.assertEqual(client.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers.get("Access-Control-Allow-Origin"), "http://localhost:5173")
            self.assertIsNone(client.get("/api/health", headers={"Origin": "https://untrusted.example"}).headers.get("Access-Control-Allow-Origin"))
            sys.modules.pop("app", None)


if __name__ == "__main__":
    unittest.main()
