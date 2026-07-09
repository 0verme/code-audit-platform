import sys
import unittest
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
SVN_CHECK_DIR = BACKEND_DIR / "svn_check"
for path in (BACKEND_DIR, SVN_CHECK_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit.hcyt_schedule_runner import run_hcyt_schedule, schedule_rows  # noqa: E402
from audit.result_normalizer import rule_label  # noqa: E402


class FakeReService:
    def __init__(self, mapping):
        self.mapping = mapping

    def load_xls_to_df(self, path):
        return self.mapping[path]


class FakeHcyt:
    def rule_excle_plan(self, plan_df):
        return ("计划 成环", "计划 警告", 0, {"plan": "PLAN_A"})

    def rule_excle_seq(self, seq_df):
        return ("", "顺序 缺失", 0)

    def rule_excle_job(self, job_df, r_plan=None, timing_log=None, job_rows=None):
        return ("作业 不存在\n作业 成环", "作业 警告", 0)


class FakePublicData:
    def all_job(self):
        return [("row",)]


class FakeModules:
    def __init__(self, mapping):
        self.re_service = FakeReService(mapping)
        self.hcyt = FakeHcyt()
        self.public_data = FakePublicData()


class HcytScheduleRunnerTests(unittest.TestCase):
    def test_schedule_rows_preserves_rule_level_and_message_shape(self):
        rows = schedule_rows("A\n\nB", "C", rule_label=rule_label)

        self.assertEqual(
            rows,
            [
                {"rule": "A", "level": "err", "msg": "A"},
                {"rule": "B", "level": "err", "msg": "B"},
                {"rule": "C", "level": "warn", "msg": "C"},
            ],
        )

    def test_run_hcyt_schedule_keeps_summary_tables_and_row_states_shape(self):
        plan_df = pd.DataFrame([["PLAN_A", "", "", "", "JOB_A"]])
        seq_df = pd.DataFrame([["PLAN_A", "FLOW_A", "desc"]])
        cale_df = pd.DataFrame([["daily", "1"]], columns=["cycle", "value"])
        job_df = pd.DataFrame([["JOB_A", "task"]])
        modules = FakeModules(
            {
                "plan.xlsx": plan_df,
                "seq.xlsx": seq_df,
                "cale.xlsx": cale_df,
                "job.xlsx": job_df,
            }
        )

        result = run_hcyt_schedule(
            "plan.xlsx",
            "seq.xlsx",
            "cale.xlsx",
            "job.xlsx",
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            build_job_table=lambda job_source, db_job_rows: (
                {"columns": ["job", "task"], "rows": [["JOB_A", "task"]]},
                [{"job": "JOB_A", "state": "new"}],
            ),
            schedule_rows_fn=lambda result_text, warn_text: schedule_rows(
                result_text,
                warn_text,
                rule_label=rule_label,
            ),
        )

        self.assertEqual(result["summary"], {"plan": 1, "seq": 1, "job": 1, "cycles": 1, "missing": 1})
        self.assertEqual(set(result["tables"].keys()), {"plan", "seq", "cale", "job"})
        self.assertEqual(result["tables"]["job"]["rowStates"], [{"job": "JOB_A", "state": "new"}])
        self.assertEqual(result["tables"]["plan"]["columns"], ["计划名", "前置依赖"])
        self.assertEqual(result["tables"]["seq"]["columns"], ["计划名", "作业流名", "作业流描述"])
        self.assertEqual(result["rows"][0]["table"], "PLAN")
        self.assertEqual(result["rows"][-1]["table"], "JOB")
        self.assertIs(result["_job_df"], job_df)
        self.assertEqual(result["_r_plan"], {"plan": "PLAN_A"})
        self.assertEqual(result["_db_job_rows"], [("row",)])


if __name__ == "__main__":
    unittest.main()
