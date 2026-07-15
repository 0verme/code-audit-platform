import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402


class FakeReService:
    def safe_remove_prefix(self, path):
        return Path(path).name

    def get_filename(self, path):
        return Path(path).name

    def read_data_from_file(self, path):
        return "create table DM.TABLE_A (id int)"

    def build_job_outfile_lookup(self, rows=None):
        return {"JOB_A": ["OUTFILE_A"]}


class FakeHcyt:
    def get_hcyt_type(self, exported):
        return (
            "C:/workspace/dws.sql",
            "C:/workspace/hive.sql",
            ["C:/workspace/schema_config.json"],
            ["C:/workspace/sbin/post.sh"],
            ["C:/workspace/recv.json"],
            [],
            [],
            None,
            None,
            ["C:/workspace/program.py"],
            None,
            None,
            None,
            None,
            None,
        )

    def rule_dws(self, path):
        return ("dws warning", "", 1)

    def rule_hive(self, path):
        return ("", "hive error", 1)

    def rule_sbin(self, paths):
        return ("sbin warning", "", 1)

    def rule_recv_json(self, paths):
        return ("recv warning", "", 1)

    def rule_config(self, paths):
        return ("", "config error", 1)


class FakeDdlRule:
    def collect_root_missing_issues(self, sql_text, source_module, source_file):
        return []


class FakeSqlRule:
    def collect_created_table_review_issues(self, path, source_module, source_file):
        return []


class FakeMetadataService:
    def list_job_outfiles(self):
        return [("JOB_A", "OUTFILE_A")]

    def list_result_table_recv_details(self):
        return [("DM.TABLE_A", "PLAN_A", "SYS_A")]

    def list_result_table_sys_names(self):
        return [("DM.TABLE_A", "SYS_B")]

    def list_recv_mapping_plans(self):
        return []


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.hcyt_ddl_rule = FakeDdlRule()
        self.hcyt_sql_rule = FakeSqlRule()
        self.audit_metadata_service = FakeMetadataService()

    def dedupe_issues(self, issues):
        return list(issues or [])

    def asset_issues_to_unified_issues(self, issues, scan_batch_id=None):
        return [
            {
                "rule_code": "asset-review",
                "object_name": "DM.TABLE_A",
                "scan_batch_id": scan_batch_id,
            }
        ]


class HcytReportContractTests(unittest.TestCase):
    def setUp(self):
        self.previous_mods = audit_engine._mods
        audit_engine._mods = FakeModules()

    def tearDown(self):
        audit_engine._mods = self.previous_mods

    def _run_hcyt(self):
        saved_groups = []
        partials = {}

        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 42
        run.repo = "svn://repo/hcyt/demo"
        run.workflow = "hcyt"
        run.ai_enabled = False
        run.debug_enabled = False
        run.author = "tester"
        run.source_type = "local"
        run.logs = []
        run.start_ts = 0
        run.update = lambda *args, **kwargs: None
        run.task_running = lambda *args, **kwargs: None
        run.task_success = lambda *args, **kwargs: None
        run.task_skipped = lambda *args, **kwargs: None
        run.set_partial = lambda key, value: partials.__setitem__(key, value)
        run.download_url = lambda path: f"download://{Path(path).name}"
        run.build_ai = lambda *args, **kwargs: None
        run.build_config_files = lambda paths: [{"path": path, "rows": []} for path in paths]
        run.run_hcyt_schedule = lambda *args, **kwargs: {
            "summary": {"plan": 1, "seq": 1, "job": 1, "cycles": 0, "missing": 0},
            "rows": [{"table": "SCHEDULE", "item": "JOB_A", "rule": "cycle", "level": "warn", "msg": "schedule warning"}],
            "tables": {"job": [{"job": "JOB_A"}]},
            "_job_df": None,
            "_r_plan": None,
            "_db_job_rows": [{"job": "JOB_A"}],
        }
        run.run_hcyt_programs = lambda *args, **kwargs: (
            [{"path": "C:/workspace/program.py"}],
            [{"file": "program.py", "line": 7, "rule": "py-rule", "level": "error", "msg": "python error"}],
            ["DM.TABLE_A"],
            [{"from": "program.py", "to": "DM.TABLE_A"}],
            [],
        )
        run.save_category_rows = lambda grouped: saved_groups.append(grouped)

        svn_result = {
            "exported_paths": [
                "C:/workspace/dws.sql",
                "C:/workspace/hive.sql",
                "C:/workspace/schema_config.json",
                "C:/workspace/sbin/post.sh",
                "C:/workspace/recv.json",
                "C:/workspace/program.py",
            ],
            "branch_changed_files": ["dws.sql"],
            "trunk_conflict_files": ["hive.sql"],
            "create_revision": "123",
            "source_type": "local",
            "workspace_root": "C:/workspace",
        }

        report = run.run_hcyt(svn_result)
        return report, saved_groups, partials, svn_result

    def test_hcyt_report_top_level_contract_is_stable(self):
        report, _saved_groups, _partials, _svn_result = self._run_hcyt()

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
            ],
        )
        self.assertEqual(
            set(report["task"].keys()),
            {
                "status",
                "repo",
                "sourceRef",
                "module",
                "workflow",
                "revision",
                "author",
                "startedAt",
                "duration",
                "sourceType",
                "workspaceRoot",
                "changedFiles",
                "checks",
                "errors",
                "warnings",
                "conflicts",
                "sqlFiles",
            },
        )
        self.assertEqual(set(report["svn"].keys()), {"branchChanged", "trunkConflict"})

    def test_partial_final_report_and_compat_sections_are_stable(self):
        report, _saved_groups, partials, _svn_result = self._run_hcyt()

        self.assertEqual(partials["changes"], report["changes"])
        self.assertEqual(partials["conflicts"], report["conflicts"])
        self.assertEqual(partials["dws"], report["dws"])
        self.assertEqual(partials["hive"], report["hive"])
        self.assertEqual(partials["python"], report["python"])
        self.assertEqual(partials["sbin"], report["sbin"])
        self.assertEqual(partials["config"], report["config"])
        self.assertEqual(partials["recv"], report["recv"])
        self.assertEqual(partials["schedule"], report["schedule"])
        self.assertEqual(partials["assetIssues"], report["assetIssues"])
        self.assertEqual(partials["unifiedAssetIssues"], report["unifiedAssetIssues"])
        self.assertEqual(partials["lineageSummary"], report["lineageSummary"])
        self.assertNotIn("audit_results", report)
        self.assertIn("unifiedAssetIssues", report)

    def test_source_payload_position_and_shape_are_stable(self):
        report, _saved_groups, _partials, svn_result = self._run_hcyt()

        self.assertEqual(report["task"]["sourceType"], svn_result["source_type"])
        self.assertEqual(report["task"]["workspaceRoot"], svn_result["workspace_root"])
        self.assertNotIn("source", report)
        self.assertNotIn("sourceType", report)
        self.assertNotIn("workspaceRoot", report)
        self.assertNotIn("source", report["svn"])

    def test_lineage_summary_contract_is_stable(self):
        report, _saved_groups, partials, _svn_result = self._run_hcyt()

        self.assertEqual(report["lineageSummary"], partials["lineageSummary"])
        self.assertEqual(
            set(report["lineageSummary"].keys()),
            {"resultTables", "jobs", "recvPlans", "sysNames", "outfiles", "warnings", "stats"},
        )
        self.assertEqual(report["lineageSummary"]["resultTables"], [])
        self.assertEqual(report["lineageSummary"]["recvPlans"], [])
        self.assertEqual(report["lineageSummary"]["sysNames"], [])
        self.assertEqual(report["lineageSummary"]["outfiles"], [])

    def test_final_report_retains_the_legacy_audit_results_projection_contract(self):
        report, saved_groups, _partials, _svn_result = self._run_hcyt()
        from app.modules.audit.compat import build_legacy_hcyt_audit_result_rows

        self.assertEqual(saved_groups, [])
        grouped = build_legacy_hcyt_audit_result_rows(report)
        self.assertEqual(list(grouped.keys()), ["dws", "hive", "python", "sbin", "config", "recv"])
        self.assertEqual([len(grouped[key]) for key in grouped], [1, 1, 1, 1, 1, 1])
        for category, rows in grouped.items():
            self.assertIsInstance(rows, list, category)
            for row in rows:
                self.assertEqual(set(row.keys()), {"file", "line", "rule", "level", "msg"})
                self.assertIsInstance(row["file"], str)
                self.assertTrue(row["line"] is None or isinstance(row["line"], int))
                self.assertIsInstance(row["rule"], str)
                self.assertIn(row["level"], {"info", "warn", "err", "error"})
                self.assertIsInstance(row["msg"], str)


if __name__ == "__main__":
    unittest.main()
