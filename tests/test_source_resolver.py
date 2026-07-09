import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.source_resolver import (  # noqa: E402
    build_source_label,
    build_source_load_step,
    build_source_summary,
    normalize_source_payload,
    resolve_workflow,
    validate_source_workflow,
)


class SourceResolverTests(unittest.TestCase):
    def test_resolve_workflow_uses_fallback_for_default_hcyt(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/demo", "hcyt"), "hcyt")

    def test_resolve_workflow_detects_nups_across_path_styles(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/NUPS/demo"), "nups")
        self.assertEqual(resolve_workflow("svn://example.com/branches/nups/demo"), "nups")
        self.assertEqual(resolve_workflow(r"C:\workspace\nups\demo"), "nups")

    def test_resolve_workflow_detects_fine_report(self):
        self.assertEqual(resolve_workflow("svn://example.com/branches/fine-report/demo"), "fine-report")

    def test_validate_source_workflow_accepts_local_hcyt(self):
        validate_source_workflow("local", "hcyt")

    def test_validate_source_workflow_rejects_local_non_hcyt(self):
        with self.assertRaisesRegex(
            ValueError,
            "^Local workspace source currently supports hcyt workflow only$",
        ):
            validate_source_workflow("local", "nups")

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
