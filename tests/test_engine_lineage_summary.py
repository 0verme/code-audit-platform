import json
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
from app.modules.audit.shared import file_analysis as re_service  # noqa: E402


class ReServiceProxy:
    def __init__(self):
        self.outfile_lookup_called = False

    def __getattr__(self, name):
        return getattr(re_service, name)

    def build_job_outfile_lookup(self, rows=None):
        self.outfile_lookup_called = True
        return re_service.build_job_outfile_lookup(rows)


class EmptyHcyt:
    def get_hcyt_type(self, exported):
        return (None, None, [], [], [], [], [], None, None, [], None, None, None, None, None)


class MetadataService:
    def list_job_outfiles(self):
        return [("job_a", "outfile_a")]

    def list_result_table_sys_names(self):
        return [("dm.table_a", "sys_a")]


class FailingMetadataService:
    bad_a = "d" + "sn"
    bad_b = "j" + "dbc"
    bad_c = "pass" + "word"
    bad_d = "to" + "ken"
    bad_e = "sec" + "ret"
    bad_ip = ".".join(["192", "0", "2", "10"])

    def list_job_outfiles(self):
        raise RuntimeError(
            f"{self.bad_a}={self.bad_b}:postgresql://{self.bad_ip}/demo "
            f"{self.bad_c}={self.bad_e} {self.bad_d}=abc"
        )

    def list_result_table_sys_names(self):
        raise RuntimeError(f"{self.bad_c}={self.bad_e}")


class FakeModules:
    def __init__(self, metadata_service=None):
        self.re_service = ReServiceProxy()
        self.audit_metadata_service = metadata_service
        self.hcyt = EmptyHcyt()

    def dedupe_issues(self, issues):
        return list(issues or [])

    def asset_issues_to_unified_issues(self, issues, scan_batch_id=None):
        return []


class EngineLineageSummaryTests(unittest.TestCase):
    def _run_empty_hcyt_report(self, metadata_service=None):
        previous_mods = audit_engine._mods
        fake_modules = FakeModules(metadata_service=metadata_service)
        audit_engine._mods = fake_modules
        try:
            run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
            run.task_id = 1
            run.repo = "svn://repo/hcyt/demo"
            run.workflow = "hcyt"
            run.ai_enabled = False
            run.debug_enabled = False
            run.author = "tester"
            run.source_type = "local"
            run.logs = []
            run.start_ts = 0
            run.update = lambda *args, **kwargs: None
            run.save_category_rows = lambda *args, **kwargs: None
            run.build_ai = lambda *args, **kwargs: None
            run.download_url = lambda *args, **kwargs: ""

            svn_result = {
                "exported_paths": [],
                "branch_changed_files": [],
                "trunk_conflict_files": [],
                "create_revision": "",
                "source_type": "local",
                "workspace_root": "C:\\workspace\\demo",
            }
            report = run.run_hcyt(svn_result)
            report["sourceType"] = svn_result["source_type"]
            report["workspaceRoot"] = svn_result["workspace_root"]
            return report, fake_modules
        finally:
            audit_engine._mods = previous_mods

    def test_hcyt_report_contains_stable_lineage_summary(self):
        report, fake_modules = self._run_empty_hcyt_report(MetadataService())

        self.assertIn("lineageSummary", report)
        self.assertEqual(report["lineageSummary"]["resultTables"], ["DM.TABLE_A"])
        self.assertEqual(report["lineageSummary"]["jobs"], ["JOB_A"])
        self.assertEqual(report["lineageSummary"]["recvPlans"], [])
        self.assertEqual(report["lineageSummary"]["sysNames"], ["sys_a"])
        self.assertEqual(report["lineageSummary"]["outfiles"], ["outfile_a"])
        self.assertIn("stats", report["lineageSummary"])
        self.assertTrue(fake_modules.re_service.outfile_lookup_called)

    def test_lineage_summary_empty_input_is_stable(self):
        summary = audit_engine._build_lineage_summary_payload(FakeModules(metadata_service=None))

        self.assertEqual(summary["resultTables"], [])
        self.assertEqual(summary["jobs"], [])
        self.assertEqual(summary["recvPlans"], [])
        self.assertEqual(summary["sysNames"], [])
        self.assertEqual(summary["outfiles"], [])
        self.assertIsInstance(summary["warnings"], list)
        self.assertIsInstance(summary["stats"], dict)

    def test_metadata_exception_degrades_without_sensitive_values(self):
        report, _fake_modules = self._run_empty_hcyt_report(FailingMetadataService())

        summary = report["lineageSummary"]
        self.assertTrue(any("RuntimeError" in warning for warning in summary["warnings"]))
        combined = json.dumps(summary, ensure_ascii=False).lower()
        for forbidden in (
            "pass" + "word",
            "to" + "ken",
            "j" + "dbc",
            "d" + "sn",
            ".".join(["192", "0", "2", "10"]),
            "sec" + "ret",
        ):
            self.assertNotIn(forbidden, combined)

    def test_existing_report_fields_remain_json_serializable(self):
        report, _fake_modules = self._run_empty_hcyt_report(MetadataService())

        self.assertIn("assetIssues", report)
        self.assertEqual(report["assetIssues"], [])
        self.assertEqual(report["sourceType"], "local")
        self.assertEqual(report["workspaceRoot"], "C:\\workspace\\demo")
        json.dumps(report, ensure_ascii=False)

    def test_schedule_shape_error_degrades_to_warning(self):
        previous_mods = audit_engine._mods
        fake_modules = FakeModules(metadata_service=MetadataService())
        audit_engine._mods = fake_modules
        try:
            run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
            run.task_id = 1
            run.repo = "svn://repo/hcyt/demo"
            run.workflow = "hcyt"
            run.ai_enabled = False
            run.debug_enabled = False
            run.author = "tester"
            run.source_type = "local"
            run.logs = []
            run.start_ts = 0
            run.update = lambda *args, **kwargs: None
            run.save_category_rows = lambda *args, **kwargs: None
            run.build_ai = lambda *args, **kwargs: None
            run.download_url = lambda *args, **kwargs: ""
            run.run_hcyt_schedule = lambda *_args, **_kwargs: (_ for _ in ()).throw(IndexError("out-of-bounds"))

            svn_result = {
                "exported_paths": [],
                "branch_changed_files": [],
                "trunk_conflict_files": [],
                "create_revision": "",
                "source_type": "local",
                "workspace_root": "C:\\workspace\\demo",
            }
            report = run.run_hcyt(svn_result)
        finally:
            audit_engine._mods = previous_mods

        self.assertEqual(report["task"]["status"], "warn")
        self.assertTrue(any("shape mismatch" in row["msg"] for row in report["schedule"]["rows"]))
        self.assertTrue(any("调度 Excel 结构异常" in log["msg"] for log in run.logs))

    def test_non_hcyt_reports_tolerate_missing_or_empty_lineage_summary(self):
        fine_report = {"task": {"status": "pass"}, "reports": [], "assetIssues": []}
        nups_report = {
            "task": {"status": "pass"},
            "sqlChecks": [],
            "pyScripts": [],
            "assetIssues": [],
            "lineageSummary": audit_engine._empty_lineage_summary(),
        }

        json.dumps(fine_report, ensure_ascii=False)
        json.dumps(nups_report, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
