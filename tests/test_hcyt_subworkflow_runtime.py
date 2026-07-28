import sys
import types
import unittest
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.hcyt.subworkflow_runtime import (  # noqa: E402
    run_hcyt_programs,
    run_hcyt_schedule,
)
from app.modules.audit.shared.findings import CheckResult  # noqa: E402
from app.modules.audit.shared.result_normalizer import dedupe_tables, normalize_table  # noqa: E402


class ScheduleModules:
    def __init__(self):
        self.re_service = types.SimpleNamespace(
            load_xls_to_df=lambda path: {
                "plan.xlsx": pd.DataFrame([["PLAN_A", "", "", "", "JOB_A"]]),
                "seq.xlsx": pd.DataFrame([["PLAN_A", "FLOW_A", "desc", ""]]),
                "cale.xlsx": pd.DataFrame([["daily", "1"]], columns=["cycle", "value"]),
                "job.xlsx": pd.DataFrame([["JOB_A", "task"]]),
            }[path]
        )
        plan_result = CheckResult(artifacts={"plans": {"plan": "PLAN_A"}})
        plan_result.add("hcyt.schedule.plan.demo", "计划示例", "err", "plan err")
        seq_result = CheckResult()
        seq_result.add("hcyt.schedule.seq.demo", "作业流示例", "warn", "seq warn")
        job_result = CheckResult()
        job_result.add("hcyt.schedule.job.demo", "作业示例", "err", "job err")
        self.hcyt = types.SimpleNamespace(
            collect_send_plan_names=lambda _job_source: set(),
            rule_excle_plan=lambda _df, **_kwargs: plan_result,
            rule_excle_seq=lambda _df: seq_result,
            rule_excle_job=lambda _df, **_kwargs: job_result,
        )
        self.public_data = types.SimpleNamespace(all_job=lambda: [("row",)])


class MinimalProgramModules:
    def __init__(self):
        self.profile_calls = []
        self.re_service = types.SimpleNamespace(
            get_filename=lambda path: Path(path).name,
            read_data_from_file=lambda _path: "",
            safe_remove_prefix=lambda path: path,
            build_job_outfile_lookup=lambda _rows: {},
        )
        self.hcyt = types.SimpleNamespace(
            rule_dws_py=lambda _path, **_kwargs: CheckResult(artifacts={"sql_tables": ["DM.TABLE_A"]}),
            get_program_table_name=lambda _path: "",
        )

    def load_registered_result_tables(self, *, profile):
        self.profile_calls.append(profile)
        return set()


class HcytSubworkflowRuntimeTests(unittest.TestCase):
    def test_schedule_wrapper_keeps_schedule_runner_shape(self):
        modules = ScheduleModules()

        result = run_hcyt_schedule(
            "plan.xlsx",
            "seq.xlsx",
            "cale.xlsx",
            "job.xlsx",
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            build_job_table=lambda _job_source, _db_job_rows, **_kwargs: (
                {"columns": ["job", "task"], "rows": [["JOB_A", "task"]]},
                [{"job": "JOB_A", "state": "new"}],
            ),
        )

        self.assertEqual(result["summary"], {"plan": 1, "seq": 1, "job": 1, "cycles": 0, "missing": 0})
        self.assertEqual(set(result["tables"].keys()), {"plan", "seq", "cale", "job"})
        self.assertEqual(result["tables"]["job"]["rowStates"], [{"job": "JOB_A", "state": "new"}])
        self.assertEqual(result["rows"][0]["table"], "PLAN")
        self.assertEqual(result["rows"][-1]["table"], "JOB")
        self.assertIsNotNone(result["_job_df"])
        self.assertEqual(result["_r_plan"], {"plan": "PLAN_A"})
        self.assertEqual(result["_db_job_rows"], [("row",)])

    def test_program_wrapper_keeps_noop_fallbacks_and_profile_routing(self):
        modules = MinimalProgramModules()
        lineage_context = {}

        py_scripts, py_rows, ref_tables, deps, asset_issues = run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df=None,
            program_xls=None,
            db_job_rows=None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: f"download://{Path(path).name}",
            load_result_table_annotations=lambda **_kwargs: (set(), {}),
            annotate_table=lambda name, disabled, sys_name_map: {
                "name": normalize_table(name),
                "disabled": False,
                "sysNames": [],
                "highlight": False,
            },
            profile_name="local_pg",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={},
            lineage_context=lineage_context,
        )

        self.assertEqual(modules.profile_calls, ["local_pg"])
        self.assertEqual(lineage_context["warnings"], ["lineage metadata unavailable"])
        self.assertEqual(py_rows, [])
        self.assertEqual(py_scripts[0]["script"], "program.py")
        self.assertEqual(py_scripts[0]["job"], "")
        self.assertEqual(py_scripts[0]["jobDisabled"], False)
        self.assertEqual(py_scripts[0]["result"], [])
        self.assertEqual(py_scripts[0]["codeval"], [])
        self.assertEqual(py_scripts[0]["temp"], ["DM.TABLE_A"])
        self.assertEqual(ref_tables, [{"name": "DM.TABLE_A", "type": "mid"}])
        self.assertEqual(deps, [])
        self.assertEqual(asset_issues, [])

    def test_program_wrapper_injects_metadata_service_for_lineage_reuse(self):
        modules = MinimalProgramModules()
        calls = []
        modules.audit_metadata_service = types.SimpleNamespace(
            list_job_outfiles=lambda: calls.append("outfiles") or [("JOB_A", "a.out")],
            list_result_table_sys_names=lambda: calls.append("sys_names") or [("DM.TABLE_A", "SYS_A")],
        )
        lineage_context = {}

        run_hcyt_programs(
            ["C:/repo/program.py"],
            job_df=None,
            program_xls=None,
            db_job_rows=None,
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            download_url=lambda path: path,
            load_result_table_annotations=lambda **_kwargs: (set(), {}),
            annotate_table=lambda name, disabled, sys_name_map: {},
            profile_name="local_pg",
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map={},
            lineage_context=lineage_context,
        )

        self.assertEqual(calls, ["outfiles", "sys_names"])
        self.assertEqual(lineage_context["job_outfile_rows"], [("JOB_A", "a.out")])
        self.assertEqual(lineage_context["result_table_sys_name_rows"], [("DM.TABLE_A", "SYS_A")])


if __name__ == "__main__":
    unittest.main()
