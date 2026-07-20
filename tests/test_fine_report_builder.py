import unittest

from app.modules.audit.fine_report_builder import build_fine_report


class FineReportBuilderTests(unittest.TestCase):
    def _inputs(self):
        return {
            "task": {"status": "warn", "workflow": "FineReport report audit"},
            "svn": {"branchChanged": ["report.cpt"], "trunkConflict": []},
            "changes": [{"type": "M", "path": "report.cpt", "downloadUrl": "/source-file?path=report.cpt"}],
            "menu_section": {"columns": ["menu"], "rows": [], "messages": []},
            "authority_section": {"columns": ["auth"], "rows": [], "messages": [{"level": "warn"}]},
            "reports": [{"title": "report", "file": "report.cpt", "issues": []}],
            "ref_tables": [{"name": "DM.TABLE_A", "type": "result"}],
        }

    def test_final_report_field_order_and_structure_are_stable(self):
        report = build_fine_report(**self._inputs())

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "changes",
                "menu",
                "authority",
                "reports",
                "refTables",
                "assetIssues",
                "unifiedAssetIssues",
            ],
        )
        self.assertEqual(report["task"]["status"], "warn")
        self.assertEqual(report["svn"], {"branchChanged": ["report.cpt"], "trunkConflict": []})
        self.assertEqual(report["changes"][0]["path"], "report.cpt")
        self.assertEqual(report["reports"][0]["file"], "report.cpt")
        self.assertEqual(report["refTables"], [{"name": "DM.TABLE_A", "type": "result"}])

    def test_partial_compatibility_sections_are_stable_empty_lists(self):
        report = build_fine_report(**self._inputs())

        self.assertEqual(report["assetIssues"], [])
        self.assertEqual(report["unifiedAssetIssues"], [])
        self.assertNotIn("audit_results", report)

    def test_optional_ai_is_appended_at_the_end(self):
        inputs = self._inputs()
        report = build_fine_report(**inputs, ai={"summary": "ok"})

        self.assertEqual(list(report.keys())[-1], "ai")
        self.assertEqual(report["ai"], {"summary": "ok"})

    def test_metadata_profile_reports_actual_read_profile(self):
        report = build_fine_report(**self._inputs(), metadata_profile="local_pg")
        self.assertEqual(report["metadataProfile"], "local_pg")

    def test_source_payload_is_not_added_to_top_level_or_svn(self):
        report = build_fine_report(**self._inputs())

        self.assertNotIn("source", report)
        self.assertNotIn("sourceType", report)
        self.assertNotIn("workspaceRoot", report)
        self.assertNotIn("source", report["svn"])


if __name__ == "__main__":
    unittest.main()
