import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.source.resolver import (  # noqa: E402
    GIT_SOURCE_UNSUPPORTED_MESSAGE,
    LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE,
    UnsupportedAuditSourceError,
    build_source_label,
    build_source_load_step,
    build_source_summary,
    normalize_source_payload,
    resolve_workspace,
    resolve_workflow,
    validate_source_workflow,
)
from app.settings import RuntimeSecuritySettings  # noqa: E402


class SourceResolverTests(unittest.TestCase):
    def test_resolve_workflow_uses_fallback_for_default_hcyt(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/demo", "hcyt"), "hcyt")

    def test_resolve_workflow_detects_nups_across_path_styles(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/NUPS/demo"), "nups")
        self.assertEqual(resolve_workflow("svn://example.com/branches/nups/demo"), "nups")
        self.assertEqual(resolve_workflow(r"C:\workspace\nups\demo"), "nups")

    def test_resolve_workflow_detects_fine_report(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/fine-report/demo"), "fine-report")

    def test_validate_source_workflow_accepts_supported_local_workflows(self):
        for workflow in ("hcyt", "nups", "fine-report"):
            with self.subTest(workflow=workflow):
                validate_source_workflow("local", workflow)

    def test_validate_source_workflow_rejects_unsupported_local_workflow(self):
        with self.assertRaisesRegex(
            ValueError,
            f"^{LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE}$",
        ):
            validate_source_workflow("local", "unknown")

    def test_build_source_label_keeps_existing_display_rules(self):
        self.assertEqual(build_source_label(r"C:\workspace\demo", "local"), "local workspace")
        self.assertEqual(
            build_source_label("svn://example.com/branches/demo", "svn"),
            "svn://example.com/branches/demo",
        )

    def test_build_source_load_step_keeps_existing_step_labels(self):
        self.assertEqual(build_source_load_step("local"), "读取本地目录")
        self.assertEqual(build_source_load_step("svn"), "拉取 SVN")

    def test_normalize_source_payload_fills_svn_defaults(self):
        payload = {"exported_paths": ["demo.sql"]}

        normalized = normalize_source_payload(payload, source_type="svn")

        self.assertEqual(normalized["source_type"], "svn")
        self.assertEqual(normalized["workspace_root"], "")
        self.assertEqual(normalized["exported_paths"], ["demo.sql"])
        self.assertNotEqual(id(normalized), id(payload))

    def test_resolve_workspace_uses_local_loader_for_local_hcyt(self):
        calls = []

        def local_loader(source_ref, workflow):
            calls.append((source_ref, workflow))
            return {"source_type": "local", "workspace_root": source_ref}

        def svn_loader(_source_ref):
            raise AssertionError("svn_loader should not be called for local source")

        resolved = resolve_workspace(
            r"C:\workspace\demo",
            "hcyt",
            "local",
            svn_loader=svn_loader,
            local_loader=local_loader,
            security_settings=RuntimeSecuritySettings(local_source_enabled=True),
        )

        self.assertEqual(calls, [(r"C:\workspace\demo", "hcyt")])
        self.assertEqual(resolved, {"source_type": "local", "workspace_root": r"C:\workspace\demo"})

    def test_resolve_workspace_rejects_unsupported_local_workflow(self):
        with self.assertRaisesRegex(
            ValueError,
            f"^{LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE}$",
        ):
            resolve_workspace(
                r"C:\workspace\unknown\demo",
                "unknown",
                "local",
                svn_loader=lambda _source_ref: None,
                local_loader=lambda _source_ref, _workflow: None,
                security_settings=RuntimeSecuritySettings(local_source_enabled=True),
            )

    def test_resolve_workspace_uses_svn_loader_and_normalizes_payload(self):
        calls = []

        def svn_loader(source_ref):
            calls.append(source_ref)
            return {"exported_paths": ["demo.sql"]}

        resolved = resolve_workspace(
            "svn://example.com/branches/demo",
            "hcyt",
            "svn",
            svn_loader=svn_loader,
            local_loader=lambda _source_ref, _workflow: None,
        )

        self.assertEqual(calls, ["svn://example.com/branches/demo"])
        self.assertEqual(resolved["source_type"], "svn")
        self.assertEqual(resolved["workspace_root"], "")
        self.assertEqual(resolved["exported_paths"], ["demo.sql"])

    def test_resolve_workspace_rejects_git_without_calling_any_loader(self):
        svn_loader = Mock()
        local_loader = Mock()

        with self.assertRaisesRegex(UnsupportedAuditSourceError, f"^{GIT_SOURCE_UNSUPPORTED_MESSAGE}$"):
            resolve_workspace(
                "git@gitlab.example.com:team/repo.git",
                "hcyt",
                "git",
                svn_loader=svn_loader,
                local_loader=local_loader,
                security_settings=RuntimeSecuritySettings(local_source_enabled=True),
            )

        svn_loader.assert_not_called()
        local_loader.assert_not_called()

    def test_resolve_workspace_propagates_local_loader_exceptions_verbatim(self):
        def local_loader(_source_ref, _workflow):
            raise RuntimeError("local loader failed")

        with self.assertRaisesRegex(RuntimeError, "^local loader failed$"):
            resolve_workspace(
                r"C:\workspace\demo",
                "hcyt",
                "local",
                svn_loader=lambda _source_ref: None,
                local_loader=local_loader,
                security_settings=RuntimeSecuritySettings(local_source_enabled=True),
            )

    def test_resolve_workspace_propagates_svn_loader_exceptions_verbatim(self):
        def svn_loader(_source_ref):
            raise RuntimeError("svn loader failed")

        with self.assertRaisesRegex(RuntimeError, "^svn loader failed$"):
            resolve_workspace(
                "svn://example.com/branches/demo",
                "hcyt",
                "svn",
                svn_loader=svn_loader,
                local_loader=lambda _source_ref, _workflow: None,
            )

    def test_build_source_summary_keeps_report_field_names_and_values(self):
        payload = {"source_type": "local", "workspace_root": r"C:\workspace\demo"}

        summary = build_source_summary(
            payload,
            source_ref=r"C:\workspace\demo",
            fallback_source_type="svn",
        )

        self.assertEqual(
            summary,
            {
                "sourceType": "local",
                "sourceRef": r"C:\workspace\demo",
                "workspaceRoot": r"C:\workspace\demo",
            },
        )
        self.assertEqual(payload, {"source_type": "local", "workspace_root": r"C:\workspace\demo"})


if __name__ == "__main__":
    unittest.main()
