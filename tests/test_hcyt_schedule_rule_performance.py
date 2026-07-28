import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.hcyt.checks import schedule_rule  # noqa: E402
from app.modules.audit.workflows.hcyt.checks.description_rule import (  # noqa: E402
    has_meaningful_job_description,
)
from app.config.audit_rules import get_audit_rules  # noqa: E402
from app.modules.audit.shared.report_helpers import build_job_table  # noqa: E402


def job_row(
    *,
    plan="PLAN_A",
    seq="SEQ_A",
    job="JOB_A",
    domain="CMS_DOMAIN",
    status="1",
    dependency="",
    parameters="",
):
    row = [""] * 28
    row[0] = plan
    row[1] = seq
    row[2] = job
    row[3] = "处理客户账户信息"
    row[5] = domain
    row[6] = "1"
    row[23] = status
    row[25] = parameters
    row[27] = dependency
    return row


class HcytScheduleRulePerformanceTests(unittest.TestCase):
    def test_missing_send_plan_is_identified_from_job_proname(self):
        plan_name = "PLAN_CUSTOM_EXPORT_DAY"
        plan_df = pd.DataFrame([[plan_name, ""]], columns=["计划名", "前置依赖"])
        job_df = pd.DataFrame([
            job_row(
                plan=plan_name,
                job="JOB_CUSTOM_EXPORT",
                parameters='--args (proname="ABC_SEND2")',
            )
        ])

        with (
            patch.object(schedule_rule, "all_plan", return_value=[]),
            patch.object(schedule_rule, "all_upstream_system_ids", return_value=[]),
        ):
            result = schedule_rule.rule_excle_plan(
                plan_df,
                send_plan_names=schedule_rule.collect_send_plan_names(job_df),
            )

        self.assertIn(
            "hcyt.schedule.plan.missing_send_plan",
            [finding.rule_code for finding in result.findings],
        )
        self.assertNotIn(
            "hcyt.schedule.plan.missing_production_plan",
            [finding.rule_code for finding in result.findings],
        )

    def test_send_named_plan_with_hyphen_proname_uses_generic_warning(self):
        plan_name = "PLAN_PROV_CUSTOM_SEND_DAY"
        plan_df = pd.DataFrame([[plan_name, ""]], columns=["计划名", "前置依赖"])
        job_df = pd.DataFrame([
            job_row(
                plan=plan_name,
                job="JOB_CUSTOM_EXPORT",
                parameters="proname=ABC-SEND3",
            )
        ])

        with (
            patch.object(schedule_rule, "all_plan", return_value=[]),
            patch.object(schedule_rule, "all_upstream_system_ids", return_value=[]),
        ):
            result = schedule_rule.rule_excle_plan(
                plan_df,
                send_plan_names=schedule_rule.collect_send_plan_names(job_df),
            )

        self.assertNotIn(
            "hcyt.schedule.plan.missing_send_plan",
            [finding.rule_code for finding in result.findings],
        )
        self.assertIn(
            "hcyt.schedule.plan.missing_production_plan",
            [finding.rule_code for finding in result.findings],
        )

    def test_plan_rule_matches_full_name_against_upstream_system_ids(self):
        plan_name = "PLAN_SA_RECV_CMS_CMS_VLOAN_DAY"
        plan_df = pd.DataFrame([[plan_name, ""]], columns=["计划名", "前置依赖"])

        with (
            patch.object(schedule_rule, "all_plan", return_value=[(plan_name,)]),
            patch.object(
                schedule_rule,
                "all_upstream_system_ids",
                return_value=[(" plan_sa_recv_cms_cms_vloan_day ",)],
            ),
        ):
            result = schedule_rule.rule_excle_plan(plan_df)

        self.assertEqual(result.findings, [])

    def test_plan_rule_warns_when_upstream_system_is_not_maintained(self):
        plan_name = "PLAN_SA_RECV_CMS_CMS_VLOAN_DAY"
        plan_df = pd.DataFrame([[plan_name, ""]], columns=["计划名", "前置依赖"])

        with (
            patch.object(schedule_rule, "all_plan", return_value=[(plan_name,)]),
            patch.object(schedule_rule, "all_upstream_system_ids", return_value=[]),
        ):
            result = schedule_rule.rule_excle_plan(plan_df)

        self.assertIn(
            f"计划名 {plan_name} 未在数据资产系统维护上游系统",
            [item.msg for item in result.findings],
        )
        self.assertFalse(any("dwp.p_upstream_system" in item.msg for item in result.findings))

    def test_named_plan_rules_do_not_depend_on_mapping_order(self):
        plan_name = "PLAN_DWS_DWD_DAY"
        plan_df = pd.DataFrame([[plan_name, ""]], columns=["计划名", "前置依赖"])
        rules = schedule_rule._schedule_rules()
        rules["plan_name_rules"] = {
            "DWM": ["PLAN_DWS_DWM_MODEL"],
            "DWP": ["PLAN_DWS_DWP_DAY"],
            "DWD": [plan_name],
        }

        with (
            patch.object(schedule_rule, "_schedule_rules", return_value=rules),
            patch.object(schedule_rule, "all_plan", return_value=[(plan_name,)]),
            patch.object(schedule_rule, "all_upstream_system_ids", return_value=[]),
        ):
            result = schedule_rule.rule_excle_plan(plan_df)

        self.assertNotIn(
            "hcyt.schedule.plan.dwd_name",
            [finding.rule_code for finding in result.findings],
        )

    def test_named_sequence_rules_do_not_depend_on_mapping_order(self):
        plan_name = "PLAN_DWS_DWD_DAY"
        sequence_name = "SEQ_DWS_DWD_DAY"
        rows = [job_row(plan=plan_name, seq=sequence_name, job="JOB_A")]
        rules = schedule_rule._schedule_rules()
        rules["sequence_name_rules"] = {
            "DWM": ["SEQ_DWS_DWM_MODEL_LON"],
            "DWP": ["SEQ_DWS_DWP_DAY"],
            "DWD": [sequence_name],
        }

        with (
            patch.object(schedule_rule, "_schedule_rules", return_value=rules),
            patch.object(schedule_rule, "all_job_outfile", return_value=[]),
            patch.object(schedule_rule, "all_cale", return_value=[], create=True),
        ):
            result = schedule_rule.rule_excle_job(
                pd.DataFrame(rows),
                r_plan={plan_name},
                job_rows=rows,
            )

        self.assertNotIn(
            "hcyt.schedule.job.dwd_sequence",
            [finding.rule_code for finding in result.findings],
        )

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
        ):
            result = schedule_rule.rule_excle_job(
                job_df,
                r_plan={"PLAN_A"},
                timing_log=timings.append,
                job_rows=rows,
            )

        self.assertEqual(load_rules.call_count, 1)
        self.assertEqual(result.findings, [])
        self.assertTrue(any("JOB Excel 转换完成" in message for message in timings))
        self.assertTrue(any("JOB规则主循环完成" in message for message in timings))

    def test_valid_edws_and_export_domains_do_not_raise_domain_findings(self):
        rows = [
            job_row(plan="PLAN_DWS_PROCESS_DAY", job="JOB_DWS_PROCESS_DAY", domain="EDWS_DOMAIN"),
            job_row(plan="PLAN_PROV_SEND_DAY", job="JOB_PROV_SEND_DAY", domain="EXPORT_DOMAIN"),
        ]

        with (
            patch.object(schedule_rule, "all_job_outfile", return_value=[]),
        ):
            result = schedule_rule.rule_excle_job(
                pd.DataFrame(rows),
                r_plan={row[0] for row in rows},
                job_rows=rows,
            )

        self.assertFalse(any(
            finding.rule_code in {
                "hcyt.schedule.job.execution_domain",
                "hcyt.schedule.job.invalid_domain",
            }
            for finding in result.findings
        ))

    def test_special_plan_still_rejects_edws_domain(self):
        rows = [
            job_row(
                plan="PLAN_SA_RECV_CMS_DAY",
                job="JOB_SA_RECV_CMS_DAY",
                domain="EDWS_DOMAIN",
            )
        ]

        with (
            patch.object(schedule_rule, "all_job_outfile", return_value=[]),
        ):
            result = schedule_rule.rule_excle_job(
                pd.DataFrame(rows),
                r_plan={rows[0][0]},
                job_rows=rows,
            )

        self.assertIn(
            "hcyt.schedule.job.execution_domain",
            [finding.rule_code for finding in result.findings],
        )

    def test_unknown_domain_still_raises_invalid_domain_finding(self):
        rows = [job_row(domain="UNKNOWN_DOMAIN")]

        with (
            patch.object(schedule_rule, "all_job_outfile", return_value=[]),
        ):
            result = schedule_rule.rule_excle_job(
                pd.DataFrame(rows),
                r_plan={rows[0][0]},
                job_rows=rows,
            )

        self.assertIn(
            "hcyt.schedule.job.invalid_domain",
            [finding.rule_code for finding in result.findings],
        )

    def test_build_job_table_preserves_rows_and_production_states(self):
        source = pd.DataFrame([
            ["PLAN_A", "SEQ_A", "job_a", "desc", "ignored"],
            ["PLAN_A", "SEQ_A", "JOB_B", None, "ignored"],
            ["PLAN_A", "SEQ_A", "JOB_C", "desc", "ignored"],
        ])
        db_rows = [job_row(job="JOB_A", status="9"), job_row(job="JOB_B", status="1")]

        timing_events = []
        table, states = build_job_table(
            source,
            db_rows,
            timing_log=lambda label, phase, **fields: timing_events.append((label, phase, fields)),
        )

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
        self.assertEqual(
            [label for label, phase, _fields in timing_events if phase == "end"],
            [
                "schedule.job.table.prepare_display",
                "schedule.job.table.build_prod_lookup",
                "schedule.job.table.serialize_rows",
                "schedule.job.table.classify_states",
            ],
        )


class HcytJobDescriptionRuleTests(unittest.TestCase):
    def setUp(self):
        self.rules = get_audit_rules()["hcyt"]["schedule"]["description_validation"]

    def test_rejects_empty_placeholder_and_non_chinese_descriptions(self):
        invalid_descriptions = [
            None,
            "",
            "   ",
            "12345",
            "audit sample",
            "ＡＵＤＩＴ　ＳＡＭＰＬＥ",
            "JOB_DWS_CUSTOMER_DAY",
            "数据采集作业",
            "数 据，采 集 作 业",
            "数据供应作业",
            "测试描述",
        ]

        for description in invalid_descriptions:
            with self.subTest(description=description):
                self.assertFalse(
                    has_meaningful_job_description(
                        description,
                        "JOB_DWS_CUSTOMER_DAY",
                        self.rules,
                    )
                )

    def test_accepts_descriptions_with_chinese_business_meaning(self):
        valid_descriptions = [
            "客户账户信息汇总",
            "加工表[客户信息]数据加工作业",
            "客户增量装载",
            "同步 customer 客户信息",
            "处理，客户　账户信息",
        ]

        for description in valid_descriptions:
            with self.subTest(description=description):
                self.assertTrue(
                    has_meaningful_job_description(
                        description,
                        "JOB_DWS_CUSTOMER_DAY",
                        self.rules,
                    )
                )

    def test_rejects_description_that_only_repeats_chinese_job_name(self):
        self.assertFalse(
            has_meaningful_job_description("客户信息作业", "客户信息", self.rules)
        )

    def test_job_rule_reports_invalid_description_without_mocking_validator(self):
        row = job_row()
        row[3] = "audit sample"

        with patch.object(schedule_rule, "all_job_outfile", return_value=[]):
            result = schedule_rule.rule_excle_job(
                pd.DataFrame([row]),
                r_plan={row[0]},
                job_rows=[row],
            )

        self.assertIn(
            "hcyt.schedule.job.description",
            [finding.rule_code for finding in result.findings],
        )


if __name__ == "__main__":
    unittest.main()
