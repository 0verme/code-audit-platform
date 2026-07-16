import sys
import types
import unittest
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_subworkflow_runtime import (  # noqa: E402
    run_hcyt_programs,
    run_hcyt_schedule,
)
from app.modules.audit.result_normalizer import dedupe_tables, normalize_table, rule_label, text_to_rows  # noqa: E402


class ScheduleModules:
    def __init__(self):
        self.re_service = types.SimpleNamespace(
            load_xls_to_df=lambda path: {
                "plan.xlsx": pd.DataFrame([["PLAN_A", "", "", "", "JOB_A"]]),
                "seq.xlsx": pd.DataFrame([["PLAN_A", "FLOW_A", "desc"]]),
                "cale.xlsx": pd.DataFrame([["daily", "1"]], columns=["cycle", "value"]),
                "job.xlsx": pd.DataFrame([["JOB_A", "task"]]),
            }[path]
        )
        self.hcyt = types.SimpleNamespace(
            rule_excle_plan=lambda _df: ("plan err", "", 0, {"plan": "PLAN_A"}),
            rule_excle_seq=lambda _df: ("", "seq warn", 0),
            rule_excle_job=lambda _df, **_kwargs: ("job err", "", 0),
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
            rule_dws_py=lambda _path, **_kwargs: ("", "", 0, ["DM.TABLE_A"]),
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
            build_job_table=lambda _job_source, _db_job_rows: (
                {"columns": ["job", "task"], "rows": [["JOB_A", "task"]]},
                [{"job": "JOB_A", "state": "new"}],
            ),
            rule_label=rule_label,
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
            text_to_rows=text_to_rows,
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


if __name__ == "__main__":
    unittest.main()
