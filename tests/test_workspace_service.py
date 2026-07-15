import sys
import tempfile
import unittest
from pathlib import Path



from app.modules.audit.checks.workspace_service import load_local_workspace  # noqa: E402
from app.settings import RuntimeSecuritySettings  # noqa: E402


class WorkspaceServiceTests(unittest.TestCase):
    def test_local_workspace_builds_unified_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            (root / ".git" / "ignored.sql").write_text("select 1", encoding="utf-8")
            (root / "DIDP_PROJECT_WORKSPACE").mkdir()
            (root / "DIDP_PROJECT_WORKSPACE" / "demo.sql").write_text("select 1", encoding="utf-8")

            info = load_local_workspace(str(root), "hcyt", RuntimeSecuritySettings(local_source_enabled=True, local_source_roots=(str(root),)))

        self.assertEqual(info["source_type"], "local")
        self.assertEqual(info["project_type"], "hcyt")
        self.assertEqual(info["changes"], ["DIDP_PROJECT_WORKSPACE/demo.sql"])
        self.assertEqual(info["branch_changed_files"], ["DIDP_PROJECT_WORKSPACE/demo.sql"])
        self.assertEqual(len(info["files"]), 1)
        self.assertTrue(info["workspace_root"])
        self.assertEqual(info["error"], "")

    def test_missing_local_workspace_error_does_not_echo_path(self):
        missing = str(Path(tempfile.gettempdir()) / "missing-workspace-example")
        with self.assertRaises(FileNotFoundError) as ctx:
            load_local_workspace(missing, security_settings=RuntimeSecuritySettings(local_source_enabled=True, local_source_roots=(tempfile.gettempdir(),)))

        message = str(ctx.exception)
        self.assertIn("does not exist", message)
        self.assertNotIn(missing, message)

    def test_empty_local_workspace_returns_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                load_local_workspace(tmp, security_settings=RuntimeSecuritySettings(local_source_enabled=True, local_source_roots=(tmp,)))

        self.assertIn("no auditable files", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
