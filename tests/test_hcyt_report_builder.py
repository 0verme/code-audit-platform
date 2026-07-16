import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_report_builder import (  # noqa: E402
    build_hcyt_final_report,
    build_hcyt_partial_report,
    build_hcyt_report,
)


def _sample_inputs():
    grouped = {
        "dws": [{"file": "dws.sql", "line": None, "rule": "", "level": "info", "msg": "dws warning"}],
        "hive": [{"file": "hive.sql", "line": None, "rule": "", "level": "err", "msg": "hive error"}],
        "python": [{"file": "program.py", "line": 7, "rule": "py-rule", "level": "error", "msg": "python error"}],
        "sbin": [{"file": "sbin", "line": None, "rule": "", "level": "info", "msg": "sbin warning"}],
        "config": [{"file": "SCHEMA_CONFIG", "line": None, "rule": "", "level": "err", "msg": "config error"}],
        "recv": [{"file": "recv_json", "line": None, "rule": "", "level": "info", "msg": "recv warning"}],
    }
    lineage_summary = {
        "resultTables": [],
        "jobs": [],
        "recvPlans": [],
        "sysNames": [],
        "outfiles": [],
        "warnings": [],
        "stats": {"resultTables": 0},
    }
    return {
        "task": {"status": "fail", "sourceType": "local", "workspaceRoot": "C:/workspace"},
        "svn": {"branchChanged": ["dws.sql"], "trunkConflict": ["hive.sql"]},
        "changes": [{"type": "M", "path": "dws.sql", "cat": "sql", "downloadUrl": ""}],
        "conflicts": [{"path": "hive.sql", "trunkRev": "trunk@HEAD", "mineRev": "r123", "note": "conflict"}],
        "grouped": grouped,
        "sql_checks": {"dws": {"script": "dws.sql", "downloadUrl": "download://dws.sql"}},
        "config_files": [{"path": "schema_config.json", "rows": []}],
        "schedule": {"summary": {"plan": 1}, "rows": [], "tables": {}},
        "py_scripts": [{"path": "program.py"}],
        "ref_tables": ["DM.TABLE_A"],
        "deps": [{"from": "program.py", "to": "DM.TABLE_A"}],
        "asset_issues": [],
        "unified_asset_issues": [{"rule_code": "asset-review", "object_name": "DM.TABLE_A"}],
        "lineage_summary": lineage_summary,
        "metadata_profile": "czcb_dws",
    }


class HcytReportBuilderTests(unittest.TestCase):
    def test_final_report_field_order_and_structure_are_stable(self):
        inputs = _sample_inputs()

        report = build_hcyt_final_report(**inputs)

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "changes",
                "conflicts",
                "dws",
                "hive",
                "python",
                "sbin",
                "config",
                "recv",
                "sqlChecks",
                "configFiles",
                "schedule",
                "pyScripts",
                "refTables",
                "deps",
                "assetIssues",
                "unifiedAssetIssues",
                "lineageSummary",
                "lineageOverlay",
                "metadataProfile",
            ],
        )
        self.assertIs(report["task"], inputs["task"])
        self.assertIs(report["svn"], inputs["svn"])
        self.assertIs(report["dws"], inputs["grouped"]["dws"])
        self.assertIs(report["sqlChecks"], inputs["sql_checks"])
        self.assertEqual(report["metadataProfile"], "czcb_dws")

    def test_report_alias_matches_final_report(self):
        inputs = _sample_inputs()

        self.assertEqual(build_hcyt_report(**inputs), build_hcyt_final_report(**inputs))

    def test_final_report_keeps_optional_ai_at_the_end(self):
        inputs = _sample_inputs()
        inputs["ai"] = {"verdict": "warn"}

        report = build_hcyt_report(**inputs)

        self.assertEqual(list(report.keys())[-1], "ai")
        self.assertEqual(report["ai"], {"verdict": "warn"})

    def test_change_and_dws_download_urls_match_for_the_same_source_file(self):
        inputs = _sample_inputs()
        download_url = "/api/audit-tasks/42/source-file?path=dws.sql"
        inputs["changes"][0]["downloadUrl"] = download_url
        inputs["sql_checks"]["dws"]["downloadUrl"] = download_url

        report = build_hcyt_final_report(**inputs)

        self.assertEqual(
            report["changes"][0]["downloadUrl"],
            report["sqlChecks"]["dws"]["downloadUrl"],
        )

    def test_partial_report_field_structure_is_stable(self):
        inputs = _sample_inputs()

        partial = build_hcyt_partial_report(
            changes=inputs["changes"],
            conflicts=inputs["conflicts"],
            grouped=inputs["grouped"],
            config_files=inputs["config_files"],
            schedule=inputs["schedule"],
            py_scripts=inputs["py_scripts"],
            ref_tables=inputs["ref_tables"],
            deps=inputs["deps"],
            asset_issues=inputs["asset_issues"],
            unified_asset_issues=inputs["unified_asset_issues"],
            lineage_summary=inputs["lineage_summary"],
        )

        self.assertEqual(
            list(partial.keys()),
            [
                "changes",
                "conflicts",
                "dws",
                "hive",
                "python",
                "sbin",
                "config",
                "recv",
                "configFiles",
                "schedule",
                "pyScripts",
                "refTables",
                "deps",
                "assetIssues",
                "unifiedAssetIssues",
                "lineageSummary",
                "lineageOverlay",
            ],
        )
        self.assertNotIn("task", partial)
        self.assertNotIn("svn", partial)

    def test_audit_results_and_asset_issue_compatibility_are_stable(self):
        inputs = _sample_inputs()

        report = build_hcyt_report(**inputs)

        self.assertNotIn("audit_results", report)
        self.assertIn("assetIssues", report)
        self.assertIn("unifiedAssetIssues", report)
        self.assertIs(report["assetIssues"], inputs["asset_issues"])
        self.assertIs(report["unifiedAssetIssues"], inputs["unified_asset_issues"])

    def test_lineage_summary_is_preserved_by_identity(self):
        inputs = _sample_inputs()

        report = build_hcyt_report(**inputs)
        partial = build_hcyt_partial_report(
            changes=inputs["changes"],
            conflicts=inputs["conflicts"],
            grouped=inputs["grouped"],
            config_files=inputs["config_files"],
            schedule=inputs["schedule"],
            py_scripts=inputs["py_scripts"],
            ref_tables=inputs["ref_tables"],
            deps=inputs["deps"],
            asset_issues=inputs["asset_issues"],
            unified_asset_issues=inputs["unified_asset_issues"],
            lineage_summary=inputs["lineage_summary"],
        )

        self.assertIs(report["lineageSummary"], inputs["lineage_summary"])
        self.assertIs(partial["lineageSummary"], inputs["lineage_summary"])

    def test_lineage_overlay_is_persisted_for_final_and_partial_reports(self):
        inputs = _sample_inputs()
        inputs["py_scripts"] = [{
            "script": "program.py", "path": "jobs/program.py", "lineageKey": "job:JOB_A",
            "job": "JOB_A", "table": "dm.table_a", "inputTables": ["ods.source_a"],
            "dependencyJobs": ["JOB_SOURCE"], "freq": "daily", "jobDisabled": False,
        }]

        report = build_hcyt_report(**inputs)
        partial = build_hcyt_partial_report(
            changes=inputs["changes"], conflicts=inputs["conflicts"], grouped=inputs["grouped"],
            config_files=inputs["config_files"], schedule=inputs["schedule"], py_scripts=inputs["py_scripts"],
            ref_tables=inputs["ref_tables"], deps=inputs["deps"], asset_issues=inputs["asset_issues"],
            unified_asset_issues=inputs["unified_asset_issues"], lineage_summary=inputs["lineage_summary"],
        )

        self.assertEqual(report["lineageOverlay"]["revision"], "")
        self.assertEqual(report["lineageOverlay"]["programs"][0]["resultTable"], "DM.TABLE_A")
        self.assertEqual(partial["lineageOverlay"]["programs"][0]["inputTables"], ["ODS.SOURCE_A"])


if __name__ == "__main__":
    unittest.main()
