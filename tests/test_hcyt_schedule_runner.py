import sys
import unittest
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_schedule_runner import run_hcyt_schedule, schedule_rows  # noqa: E402
from app.modules.audit.result_normalizer import rule_label  # noqa: E402


class FakeReService:
    def __init__(self, mapping):
        self.mapping = mapping

    def load_xls_to_df(self, path):
        return self.mapping[path]


class FakeHcyt:
    def __init__(self):
        self.job_rule_timing_log = None

    def rule_excle_plan(self, plan_df):
        return ("计划 成环", "计划 警告", 0, {"plan": "PLAN_A"})

    def rule_excle_seq(self, seq_df):
        return ("", "顺序 缺失", 0)

    def rule_excle_job(self, job_df, r_plan=None, timing_log=None, job_rows=None):
        self.job_rule_timing_log = timing_log
        if timing_log is not None:
            timing_log("JOB规则主循环完成：1 行，0.01s")
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
            build_job_table=lambda job_source, db_job_rows, **_kwargs: (
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

    def test_run_hcyt_schedule_forwards_job_rule_detail_timings(self):
        job_df = pd.DataFrame([["JOB_A", "task"]])
        modules = FakeModules({"job.xlsx": job_df})
        timing_events = []

        run_hcyt_schedule(
            None,
            None,
            None,
            "job.xlsx",
            safe=lambda _label, fn, _default: fn(),
            modules=modules,
            build_job_table=lambda _job_source, _db_job_rows, **_kwargs: (
                {"columns": ["job", "task"], "rows": [["JOB_A", "task"]]},
                ["new"],
            ),
            schedule_rows_fn=lambda result_text, warn_text: schedule_rows(
                result_text,
                warn_text,
                rule_label=rule_label,
            ),
            log_timing=lambda label, phase, **fields: timing_events.append((label, phase, fields)),
        )

        self.assertIsNotNone(modules.hcyt.job_rule_timing_log)
        self.assertIn(
            (
                "schedule.job.rules.detail",
                "point",
                {"message": "JOB规则主循环完成：1 行，0.01s"},
            ),
            timing_events,
        )
        self.assertTrue(any(
            label == "schedule.job.load_excel"
            and phase == "end"
            and fields["rows"] == 1
            and fields["columns"] == 2
            for label, phase, fields in timing_events
        ))
        self.assertTrue(any(
            label == "schedule.job.build_messages"
            and phase == "end"
            and fields["rows"] == 3
            for label, phase, fields in timing_events
        ))


if __name__ == "__main__":
    unittest.main()
