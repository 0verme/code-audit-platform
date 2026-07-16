import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.checks.hcyt import schedule_rule  # noqa: E402
from app.modules.audit.report_builder import build_job_table  # noqa: E402


def job_row(*, plan="PLAN_A", seq="SEQ_A", job="JOB_A", status="1", dependency=""):
    row = [""] * 28
    row[0] = plan
    row[1] = seq
    row[2] = job
    row[3] = "valid description"
    row[5] = "CMS_DOMAIN"
    row[6] = "1"
    row[23] = status
    row[27] = dependency
    return row


class HcytScheduleRulePerformanceTests(unittest.TestCase):
    def test_job_rule_reuses_rules_and_job_records_without_iterrows(self):
        rows = [job_row(job="JOB_A"), job_row(job="JOB_B", dependency="33:JOB_A")]
        job_df = pd.DataFrame(rows)
        job_df.iterrows = Mock(side_effect=AssertionError("iterrows should not be used"))
        rules = schedule_rule._schedule_rules()
        rules["allowed_domains"] = ["CMS_DOMAIN"]
        timings = []

        with (
            patch.object(schedule_rule, "_schedule_rules", return_value=rules) as load_rules,
            patch.object(schedule_rule, "all_job_outfile", return_value=[]),
            patch.object(schedule_rule, "ifmiaoshu", return_value=False),
        ):
            result = schedule_rule.rule_excle_job(
                job_df,
                r_plan={"PLAN_A"},
                timing_log=timings.append,
                job_rows=rows,
            )

        self.assertEqual(load_rules.call_count, 1)
        self.assertEqual(result, ("", "", 0))
        self.assertTrue(any("JOB Excel 转换完成" in message for message in timings))
        self.assertTrue(any("JOB规则主循环完成" in message for message in timings))

    def test_build_job_table_preserves_rows_and_production_states(self):
        source = pd.DataFrame([
            ["PLAN_A", "SEQ_A", "job_a", "desc", "ignored"],
            ["PLAN_A", "SEQ_A", "JOB_B", None, "ignored"],
            ["PLAN_A", "SEQ_A", "JOB_C", "desc", "ignored"],
        ])
        db_rows = [job_row(job="JOB_A", status="9"), job_row(job="JOB_B", status="1")]

        table, states = build_job_table(source, db_rows)

        self.assertEqual(table["columns"], ["计划名", "作业流名", "作业名", "作业描述"])
        self.assertEqual(
            table["rows"],
            [
                ["PLAN_A", "SEQ_A", "job_a", "desc"],
                ["PLAN_A", "SEQ_A", "JOB_B", ""],
                ["PLAN_A", "SEQ_A", "JOB_C", "desc"],
            ],
        )
        self.assertEqual(states, ["disabled", "", "new"])


if __name__ == "__main__":
    unittest.main()
