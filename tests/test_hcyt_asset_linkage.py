import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.shared.file_analysis import extract_pronames, has_send_proname  # noqa: E402
from app.modules.audit.shared.findings import CheckResult  # noqa: E402
from app.modules.audit.workflows.hcyt.checks import schedule_rule, sql_rule  # noqa: E402
from app.modules.audit.workflows.hcyt.checks.sensitive_sql import (  # noqa: E402
    extract_write_table_operations,
)
from app.modules.metadata.services.audit_metadata_service import MetadataQueryUnavailable  # noqa: E402


def job_row(job_name, parameters):
    row = [""] * 28
    row[2] = job_name
    row[25] = parameters
    return row


class PronamePushDetectionTests(unittest.TestCase):
    def test_extracts_multiple_pronames_across_supported_boundaries(self):
        value = "-x:1:(proname=abc_send):0 proname = 'risk-SEND2';proname=abc_send"
        self.assertEqual(extract_pronames(value), ["ABC_SEND", "RISK-SEND2"])

    def test_send_suffix_requires_separator_and_supported_variant(self):
        for value in [
            "proname=ABC_SEND",
            "proname=abc_send1",
            "proname=ABC_SEND3",
            "proname=ABC_SEND10",
            "proname=ABC_SEND2026",
        ]:
            with self.subTest(value=value):
                self.assertTrue(has_send_proname(value))
        for value in [
            "proname=NOTSEND",
            "proname=ABC-SEND1",
            "proname=ABC-SEND3",
            "proname=ABC_SENDX",
            "proname=SEND",
        ]:
            with self.subTest(value=value):
                self.assertFalse(has_send_proname(value))

    def test_uploaded_z_column_overrides_production_baseline(self):
        production = [job_row("JOB_A", "proname=BASE_SEND")]
        uploaded = [job_row("JOB_A", "proname=BASE_LOAD")]
        self.assertEqual(schedule_rule._collect_send_job_names(uploaded, production), {})

        uploaded[0][25] = "proname=BASE_SEND1"
        self.assertEqual(
            schedule_rule._collect_send_job_names(uploaded, production),
            {"JOB_A": ["BASE_SEND1"]},
        )


class PushRegistrationFindingTests(unittest.TestCase):
    def _findings(self, rows):
        result = CheckResult()
        with patch.object(schedule_rule, "all_push_job_systems", return_value=rows):
            schedule_rule._add_push_registration_findings(result, {"JOB_A": ["MODE_SEND"]})
        return {finding.rule_code for finding in result.findings}

    def test_reports_missing_job(self):
        self.assertEqual(
            self._findings([]),
            {"hcyt.schedule.job.push_job_missing"},
        )

    def test_reports_disabled_job_missing_system_and_disabled_system(self):
        self.assertEqual(
            self._findings([("JOB_A", "N", "", "")]),
            {
                "hcyt.schedule.job.push_job_disabled",
                "hcyt.schedule.job.push_system_missing",
            },
        )
        self.assertEqual(
            self._findings([("JOB_A", "Y", "SYS_A", "disabled")]),
            {"hcyt.schedule.job.push_system_disabled"},
        )

    def test_enabled_job_and_system_pass(self):
        self.assertEqual(self._findings([(" job_a ", "Y", "SYS_A", "enabled")]), set())

    def test_metadata_failure_is_not_reported_as_missing_registration(self):
        result = CheckResult()
        with patch.object(
            schedule_rule,
            "all_push_job_systems",
            side_effect=MetadataQueryUnavailable("push"),
        ):
            schedule_rule._add_push_registration_findings(result, {"JOB_A": ["MODE_SEND"]})
        self.assertEqual(
            [finding.rule_code for finding in result.findings],
            ["hcyt.schedule.job.asset_metadata_unavailable"],
        )


class ManualCodeTableWriteTests(unittest.TestCase):
    SQL = """
        SELECT * FROM dwp.code_a;
        INSERT INTO "dwp"."code_a" SELECT 1;
        UPDATE dwp.code_b SET value = 1;
        DELETE FROM dwp.code_c WHERE id = 1;
        MERGE INTO dwp.code_d USING src ON 1 = 1 WHEN MATCHED THEN UPDATE SET id = 2;
        TRUNCATE TABLE dwp.code_e;
        ALTER TABLE dwp.code_f ADD COLUMN note VARCHAR(20);
        DROP TABLE IF EXISTS dwp.code_g;
    """

    def test_extracts_only_mutating_table_targets(self):
        operations = extract_write_table_operations(self.SQL)
        self.assertEqual(
            [(item.operation, item.table_name.replace('"', "")) for item in operations],
            [
                ("INSERT", "dwp.code_a"),
                ("UPDATE", "dwp.code_b"),
                ("DELETE", "dwp.code_c"),
                ("MERGE", "dwp.code_d"),
                ("TRUNCATE TABLE", "dwp.code_e"),
                ("ALTER TABLE", "dwp.code_f"),
                ("DROP TABLE", "dwp.code_g"),
            ],
        )

    def test_warns_only_for_registered_written_tables(self):
        with patch.object(
            sql_rule,
            "all_manual_code_tables",
            return_value=[("CODE_A", "active"), ("CODE_E", "disabled")],
        ):
            findings = sql_rule.collect_manual_code_table_write_findings(self.SQL)
        self.assertEqual(
            [finding.rule_code for finding in findings],
            [
                "hcyt.sql.manual_code_table_write",
                "hcyt.sql.manual_code_table_write",
            ],
        )
        self.assertEqual(
            [finding.evidence["tableCode"] for finding in findings],
            ["CODE_A", "CODE_E"],
        )

    def test_metadata_failure_produces_diagnostic_only(self):
        with patch.object(
            sql_rule,
            "all_manual_code_tables",
            side_effect=MetadataQueryUnavailable("manual"),
        ):
            findings = sql_rule.collect_manual_code_table_write_findings("UPDATE dwp.code_a SET x = 1")
        self.assertEqual(
            [finding.rule_code for finding in findings],
            ["hcyt.sql.asset_metadata_unavailable"],
        )


if __name__ == "__main__":
    unittest.main()
