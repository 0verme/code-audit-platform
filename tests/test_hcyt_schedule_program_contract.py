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
        return ""

    def build_job_outfile_lookup(self, rows=None):
        return {}

    def tail_path(self, path, levels):
        return path


class FakeHcyt:
    def get_hcyt_type(self, exported):
        return (
            None,
            None,
            [],
            [],
            [],
            [],
            [],
            None,
            None,
            ["C:/workspace/program.py"],
            "C:/workspace/plan.xlsx",
            "C:/workspace/seq.xlsx",
            "C:/workspace/job.xlsx",
            "C:/workspace/program.xlsx",
            "C:/workspace/cale.xlsx",
        )


class FakeModules:
    def __init__(self):
        self.re_service = FakeReService()
        self.hcyt = FakeHcyt()
        self.audit_metadata_service = None

    def dedupe_issues(self, issues):
        return list(issues or [])

    def asset_issues_to_unified_issues(self, issues, scan_batch_id=None):
        return [{"scan_batch_id": scan_batch_id}] if issues else []


class HcytScheduleProgramContractTests(unittest.TestCase):
    def setUp(self):
        self.previous_mods = audit_engine._mods
        audit_engine._mods = FakeModules()

    def tearDown(self):
        audit_engine._mods = self.previous_mods

    def _run_hcyt(self, *, schedule=None, schedule_exc=None, programs=None):
        partials = {}
        partial_order = []
        task_events = []
        logs = []

        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 77
        run.repo = "svn://repo/hcyt/demo"
        run.workflow = "hcyt"
        run.ai_enabled = False
        run.debug_enabled = False
        run.author = "tester"
        run.source_type = "local"
        run.logs = logs
        run.start_ts = 0
        run.update = lambda *args, **kwargs: None
        run.download_url = lambda path: f"download://{Path(path).name}"
        run.build_ai = lambda *args, **kwargs: None
        run.save_category_rows = lambda *args, **kwargs: None
        run.log = lambda msg, level="INFO": logs.append({"msg": msg, "level": level})
        run.task_running = lambda key: task_events.append(("running", key))
        run.task_success = lambda key, result=None, summary=None: task_events.append(("success", key, result, summary))
        run.task_skipped = lambda key, reason=None: task_events.append(("skipped", key, reason))

        def set_partial(key, value):
            partials[key] = value
            partial_order.append(key)

        run.set_partial = set_partial

        if schedule is None:
            schedule = {
                "summary": {"plan": 1, "seq": 1, "job": 1, "cycles": 0, "missing": 0},
                "rows": [{"table": "SCHEDULE", "item": "JOB_A", "rule": "cycle", "level": "warn", "msg": "schedule warning"}],
                "tables": {"job": [{"job": "JOB_A"}]},
                "_job_df": "JOB_DF",
                "_r_plan": "R_PLAN",
                "_db_job_rows": [{"job": "JOB_A"}],
            }

        def run_schedule(*_args):
            if schedule_exc is not None:
                raise schedule_exc
            return dict(schedule)

        run.run_hcyt_schedule = run_schedule

        if programs is None:
            programs = (
                [{"script": "program.py", "path": "C:/workspace/program.py"}],
                [{"file": "program.py", "rule": "py-rule", "level": "err", "msg": "program error"}],
                [{"name": "DM.TABLE_A", "type": "result"}],
                [{"lane": "job", "nodes": [{"name": "JOB_A"}]}],
                [{"rule": "asset-review"}],
            )

        run.run_hcyt_programs = lambda *args, **kwargs: programs

        svn_result = {
            "exported_paths": ["C:/workspace/program.py"],
            "branch_changed_files": [],
            "trunk_conflict_files": [],
            "create_revision": "123",
            "source_type": "local",
            "workspace_root": "C:/workspace",
        }

        report = run.run_hcyt(svn_result)
        return report, partials, partial_order, task_events, logs

    def test_schedule_result_location_and_partial_order_are_stable(self):
        report, partials, partial_order, task_events, _logs = self._run_hcyt()

        self.assertEqual(partials["schedule"], report["schedule"])
        self.assertNotIn("_job_df", report["schedule"])
        self.assertNotIn("_r_plan", report["schedule"])
        self.assertNotIn("_db_job_rows", report["schedule"])
        self.assertLess(partial_order.index("schedule"), partial_order.index("python"))
        self.assertLess(partial_order.index("schedule"), partial_order.index("lineageSummary"))
        schedule_success = [event for event in task_events if event[:2] == ("success", "schedule")][0]
        self.assertEqual(schedule_success[3], {"issues": 1})

    def test_schedule_index_error_degrades_to_current_warning_shape(self):
        report, partials, partial_order, _task_events, logs = self._run_hcyt(
            schedule_exc=IndexError("bad columns")
        )

        self.assertEqual(partials["schedule"], report["schedule"])
        self.assertEqual(report["schedule"]["summary"], {"plan": 0, "seq": 0, "job": 0, "cycles": 0, "missing": 0})
        self.assertEqual(report["schedule"]["tables"], {})
        self.assertEqual(report["schedule"]["rows"][0]["table"], "SCHEDULE")
        self.assertEqual(report["schedule"]["rows"][0]["rule"], "column-check")
        self.assertEqual(report["schedule"]["rows"][0]["level"], "warn")
        self.assertIn("schedule artifact shape mismatch: bad columns", report["schedule"]["rows"][0]["msg"])
        self.assertLess(partial_order.index("schedule"), partial_order.index("python"))
        self.assertTrue(any(log["level"] == "WARN" for log in logs))

    def test_program_result_locations_are_stable(self):
        report, partials, partial_order, task_events, _logs = self._run_hcyt()

        self.assertEqual(partials["python"], report["python"])
        self.assertEqual(partials["pyScripts"], report["pyScripts"])
        self.assertEqual(partials["refTables"], report["refTables"])
        self.assertEqual(partials["deps"], report["deps"])
        self.assertEqual(len(report["assetIssues"]), 1)
        self.assertEqual(
            set(report["assetIssues"][0].keys()),
            {
                "issueType",
                "issueTitle",
                "issueDesc",
                "severity",
                "sourceModule",
                "sourceRule",
                "sourceFile",
                "schemaName",
                "tableName",
                "objectName",
                "fieldName",
                "rootWord",
                "suggestion",
                "portalModule",
                "portalUrl",
                "actionLabel",
                "hashKey",
                "assetType",
                "issueKey",
            },
        )
        self.assertEqual(report["unifiedAssetIssues"], [{"scan_batch_id": 77}])
        self.assertLess(partial_order.index("python"), partial_order.index("assetIssues"))
        program_success = [event for event in task_events if event[:2] == ("success", "python_scripts")][0]
        self.assertEqual(program_success[3], {"issues": 1})

    def test_program_empty_result_degrades_to_empty_compat_sections(self):
        report, partials, partial_order, _task_events, _logs = self._run_hcyt(
            programs=([], [], [], [], [])
        )

        self.assertEqual(report["python"], [])
        self.assertEqual(report["pyScripts"], [])
        self.assertEqual(report["refTables"], [])
        self.assertEqual(report["deps"], [])
        self.assertEqual(report["assetIssues"], [])
        self.assertEqual(report["unifiedAssetIssues"], [])
        self.assertEqual(partials["python"], [])
        self.assertLess(partial_order.index("python"), partial_order.index("lineageSummary"))

    def test_lineage_summary_shape_and_location_are_stable(self):
        report, partials, partial_order, task_events, _logs = self._run_hcyt()

        self.assertEqual(partials["lineageSummary"], report["lineageSummary"])
        self.assertEqual(
            set(report["lineageSummary"].keys()),
            {"resultTables", "jobs", "recvPlans", "sysNames", "outfiles", "warnings", "stats"},
        )
        self.assertLess(partial_order.index("unifiedAssetIssues"), partial_order.index("lineageSummary"))
        lineage_success = [event for event in task_events if event[:2] == ("success", "lineage")][0]
        self.assertEqual(lineage_success[3], report["lineageSummary"]["stats"])


if __name__ == "__main__":
    unittest.main()
