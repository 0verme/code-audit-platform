import unittest

from backend.audit.nups_report_builder import build_nups_report


class NupsReportBuilderTests(unittest.TestCase):
    def _inputs(self):
        return {
            "task": {"status": "fail", "workflow": "NUPS"},
            "svn": {"branchChanged": ["query.sql"], "trunkConflict": []},
            "changes": [{"path": "query.sql", "kind": "modified"}],
            "conflicts": [{"path": "conflict.sql", "type": "trunk"}],
            "sql_checks": [{"script": "query.sql", "messages": [{"level": "err", "msg": "bad"}]}],
            "py_scripts": [{"script": "job.py", "messages": [], "sqlRefs": ["DM.TABLE_A"]}],
        }

    def test_final_report_field_order_and_structure_are_stable(self):
        report = build_nups_report(**self._inputs())

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "changes",
                "conflicts",
                "sqlChecks",
                "pyScripts",
                "assetIssues",
                "unifiedAssetIssues",
            ],
        )
        self.assertEqual(report["task"]["status"], "fail")
        self.assertEqual(report["svn"], {"branchChanged": ["query.sql"], "trunkConflict": []})
        self.assertEqual(report["sqlChecks"][0]["script"], "query.sql")
        self.assertEqual(report["pyScripts"][0]["sqlRefs"], ["DM.TABLE_A"])

    def test_partial_compatibility_sections_are_stable_empty_lists(self):
        report = build_nups_report(**self._inputs())

        self.assertEqual(report["assetIssues"], [])
        self.assertEqual(report["unifiedAssetIssues"], [])
        self.assertNotIn("audit_results", report)

    def test_optional_ai_is_appended_at_the_end(self):
        inputs = self._inputs()
        report = build_nups_report(**inputs, ai={"summary": "ok"})

        self.assertEqual(list(report.keys())[-1], "ai")
        self.assertEqual(report["ai"], {"summary": "ok"})

    def test_source_payload_is_not_added_to_top_level_or_svn(self):
        report = build_nups_report(**self._inputs())

        self.assertNotIn("source", report)
        self.assertNotIn("sourceType", report)
        self.assertNotIn("workspaceRoot", report)
        self.assertNotIn("source", report["svn"])


if __name__ == "__main__":
    unittest.main()
