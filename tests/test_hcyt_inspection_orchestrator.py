import unittest

from backend.audit.hcyt_inspection_orchestrator import (
    build_schedule_shape_mismatch_result,
    run_hcyt_inspections,
)


class FakeModules:
    def __init__(self):
        self.unified_calls = []

    def dedupe_issues(self, issues):
        return list(issues or [])

    def asset_issues_to_unified_issues(self, issues, scan_batch_id=None):
        self.unified_calls.append((issues, scan_batch_id))
        return [{"scan_batch_id": scan_batch_id, "count": len(issues)}]


class HcytInspectionOrchestratorTests(unittest.TestCase):
    def _run(self, *, schedule=None, schedule_exc=None, programs=None, lineage=None):
        modules = FakeModules()
        events = []
        grouped = {"python": []}

        if schedule is None:
            schedule = {
                "summary": {"plan": 1, "seq": 0, "job": 1, "cycles": 0, "missing": 0},
                "rows": [{"level": "warn"}],
                "tables": {"job": [{"job": "JOB_A"}]},
                "_job_df": "JOB_DF",
                "_r_plan": "R_PLAN",
                "_db_job_rows": ["DB_JOB"],
            }

        if programs is None:
            programs = (
                [{"script": "program.py"}],
                [{"file": "program.py", "level": "err"}],
                [{"name": "DM.TABLE_A", "type": "result"}],
                [{"lane": "job"}],
                [{"source_rule": "asset"}],
            )

        if lineage is None:
            lineage = {
                "resultTables": ["DM.TABLE_A"],
                "jobs": ["JOB_A"],
                "recvPlans": [],
                "sysNames": [],
                "outfiles": [],
                "warnings": [],
                "stats": {"resultTables": 1},
            }

        def run_schedule(*args):
            events.append(("schedule_args", args))
            if schedule_exc is not None:
                raise schedule_exc
            return dict(schedule)

        def run_programs(*args):
            events.append(("program_args", args))
            return programs

        def build_lineage(*args, **kwargs):
            events.append(("lineage_args", args, kwargs))
            return lineage

        result = run_hcyt_inspections(
            plan_xls="plan.xlsx",
            seq_xls="seq.xlsx",
            cale_xls="cale.xlsx",
            job_xls="job.xlsx",
            py_lists=["program.py"],
            program_xls="program.xlsx",
            task_id=42,
            initial_asset_issues=[{"source_rule": "sql"}],
            run_schedule=run_schedule,
            run_programs=run_programs,
            build_lineage_summary=build_lineage,
            modules=modules,
            log_schedule_warning=lambda msg: events.append(("warn", msg)),
            update_progress=lambda **kwargs: events.append(("update", kwargs)),
            task_running=lambda key: events.append(("running", key)),
            task_success=lambda key, result=None, summary=None: events.append(("success", key, result, summary)),
            set_partial=lambda key, value: events.append(("partial", key, value)),
            grouped=grouped,
        )
        return result, modules, events

    def test_schedule_normal_result_and_hooks_are_stable(self):
        result, _modules, events = self._run()

        self.assertEqual(result.schedule["summary"]["plan"], 1)
        self.assertNotIn("_job_df", result.schedule)
        self.assertEqual(events[0][0], "schedule_args")
        self.assertEqual(events[1][0:2], ("partial", "schedule"))
        self.assertEqual(events[2][0:2], ("success", "schedule"))

    def test_schedule_exception_uses_current_warning_degradation(self):
        result, _modules, events = self._run(schedule_exc=IndexError("bad sheet"))

        expected = build_schedule_shape_mismatch_result(IndexError("bad sheet"))
        for key in ("_job_df", "_r_plan", "_db_job_rows"):
            expected.pop(key)
        self.assertEqual(result.schedule, expected)
        self.assertEqual(events[1][0], "warn")
        self.assertIn("bad sheet", events[1][1])
        self.assertEqual(events[2][0:2], ("partial", "schedule"))

    def test_program_results_and_asset_unification_are_stable(self):
        result, modules, events = self._run()

        self.assertEqual(result.py_scripts, [{"script": "program.py"}])
        self.assertEqual(result.py_rows, [{"file": "program.py", "level": "err"}])
        self.assertEqual(result.ref_tables, [{"name": "DM.TABLE_A", "type": "result"}])
        self.assertEqual(result.deps, [{"lane": "job"}])
        self.assertEqual(result.unified_asset_issues, [{"scan_batch_id": 42, "count": 2}])
        self.assertEqual(modules.unified_calls[0][1], 42)
        self.assertEqual([event[0] for event in events[3:6]], ["update", "running", "program_args"])

    def test_lineage_summary_result_and_hook_order_are_stable(self):
        result, _modules, events = self._run()

        self.assertEqual(result.lineage_summary["resultTables"], ["DM.TABLE_A"])
        self.assertEqual(result.lineage_summary["stats"], {"resultTables": 1})
        self.assertEqual([event[0] for event in events[-6:]], ["running", "lineage_args", "partial", "partial", "partial", "success"])

    def test_lineage_degraded_payload_is_preserved(self):
        degraded = {
            "resultTables": [],
            "jobs": [],
            "recvPlans": [],
            "sysNames": [],
            "outfiles": [],
            "warnings": ["lineage summary unavailable"],
            "stats": {},
        }

        result, _modules, _events = self._run(lineage=degraded)

        self.assertIs(result.lineage_summary, degraded)


if __name__ == "__main__":
    unittest.main()
