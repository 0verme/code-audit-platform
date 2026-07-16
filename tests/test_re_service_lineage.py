import logging
import sys
import unittest
from pathlib import Path



from app.modules.audit.checks import re_service  # noqa: E402


class RowLike:
    def __init__(self, **values):
        self._mapping = values


class AttrRow:
    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)


class FailingMetadataService:
    def list_job_outfiles(self):
        raise RuntimeError(
            "dsn=jdbc:postgresql://192.0.2.10/demo password=secret token=abc"
        )

    def list_result_table_sys_names(self):
        raise RuntimeError("boom")


class ReServiceLineageTests(unittest.TestCase):
    def test_build_job_outfile_lookup_handles_tuple_rows(self):
        rows = [(" job_a ", " outfile_a "), ("JOB_B", "outfile_b")]

        self.assertEqual(
            re_service.build_job_outfile_lookup(rows),
            {"JOB_A": "outfile_a", "JOB_B": "outfile_b"},
        )

    def test_build_job_outfile_lookup_handles_dict_rows(self):
        rows = [
            {"job_name": " job_a ", "outfile": " outfile_a "},
            {"a": "job_b", "b": "outfile_b"},
        ]

        self.assertEqual(
            re_service.build_job_outfile_lookup(rows),
            {"JOB_A": "outfile_a", "JOB_B": "outfile_b"},
        )

    def test_build_job_outfile_lookup_handles_row_like_rows(self):
        rows = [
            RowLike(job_name=" job_a ", outfile=" outfile_a "),
            AttrRow(job_name="job_b", outfile="outfile_b"),
        ]

        self.assertEqual(
            re_service.build_job_outfile_lookup(rows),
            {"JOB_A": "outfile_a", "JOB_B": "outfile_b"},
        )

    def test_build_job_outfile_lookup_cleans_empty_and_duplicate_rows(self):
        rows = [
            (" job_a ", " outfile_a "),
            ("JOB_A", "outfile_a"),
            ("JOB_A", "outfile_a_duplicate"),
            ("job_b", ""),
            ("", "outfile_c"),
            None,
        ]

        self.assertEqual(
            re_service.build_job_outfile_lookup(rows),
            {"JOB_A": "outfile_a"},
        )

    def test_build_job_outfile_lookup_returns_empty_for_empty_input(self):
        self.assertEqual(re_service.build_job_outfile_lookup(None), {})
        self.assertEqual(re_service.build_job_outfile_lookup([]), {})

    def test_build_wide_table_lineage_summary_returns_stable_empty_structure(self):
        summary = re_service.build_wide_table_lineage_summary()

        self.assertEqual(summary["resultTables"], [])
        self.assertEqual(summary["jobs"], [])
        self.assertEqual(summary["recvPlans"], [])
        self.assertEqual(summary["sysNames"], [])
        self.assertEqual(summary["outfiles"], [])
        self.assertEqual(
            summary["stats"],
            {
                "resultTableCount": 0,
                "jobCount": 0,
                "recvPlanCount": 0,
                "sysNameCount": 0,
                "outfileCount": 0,
            },
        )
        self.assertIn("empty lineage metadata", summary["warnings"])

    def test_build_wide_table_lineage_summary_aggregates_metadata(self):
        summary = re_service.build_wide_table_lineage_summary(
            job_outfile_rows=[
                ("job_a", "outfile_a"),
                {"job_name": "JOB_B", "outfile": "outfile_b"},
            ],
            result_table_sys_name_rows=[
                ("dm.table_a", "sys_a"),
                {"target_table_name": "dm.table_b", "system_name": "sys_b"},
            ],
        )

        self.assertEqual(summary["resultTables"], ["DM.TABLE_A", "DM.TABLE_B"])
        self.assertEqual(summary["jobs"], ["JOB_A", "JOB_B"])
        self.assertEqual(summary["recvPlans"], [])
        self.assertEqual(summary["sysNames"], ["sys_a", "sys_b"])
        self.assertEqual(summary["outfiles"], ["outfile_a", "outfile_b"])
        self.assertEqual(summary["stats"]["resultTableCount"], 2)

    def test_build_wide_table_lineage_summary_dedupes_records(self):
        summary = re_service.build_wide_table_lineage_summary(
            job_outfile_rows=[("job_a", "outfile_a"), ("JOB_A", "outfile_a")],
            result_table_sys_name_rows=[
                ("dm.table_a", "sys_a"),
                ("DM.TABLE_A", "sys_a"),
            ],
        )

        self.assertEqual(summary["resultTables"], ["DM.TABLE_A"])
        self.assertEqual(summary["jobs"], ["JOB_A"])
        self.assertEqual(summary["recvPlans"], [])
        self.assertEqual(summary["sysNames"], ["sys_a"])
        self.assertEqual(summary["outfiles"], ["outfile_a"])

    def test_build_wide_table_lineage_summary_degrades_on_metadata_exception(self):
        summary = re_service.build_wide_table_lineage_summary(
            metadata_service=FailingMetadataService()
        )

        self.assertEqual(summary["resultTables"], [])
        self.assertEqual(summary["jobs"], [])
        self.assertEqual(summary["outfiles"], [])
        self.assertTrue(any("RuntimeError" in warning for warning in summary["warnings"]))

    def test_sensitive_values_do_not_enter_summary_or_logs(self):
        logger = logging.getLogger("svn_check.audit_metadata")

        with self.assertLogs(logger, level=logging.WARNING) as logs:
            logger.warning(
                "lineage degraded function=%s error=%s",
                "mock",
                type(RuntimeError("dsn=jdbc password=secret token=abc")).__name__,
            )
            summary = re_service.build_wide_table_lineage_summary(
                job_outfile_rows=[
                    ("job_a", "dsn=jdbc:postgresql://192.0.2.10/demo password=secret token=abc")
                ],
                result_table_sys_name_rows=[
                    ("dm.table_a", "jdbc:postgresql://192.0.2.10/demo"),
                    ("dm.table_b", "sys_b"),
                ],
            )

        combined = (str(summary) + "\n" + "\n".join(logs.output)).lower()
        for forbidden in ["password", "token", "jdbc", "dsn", "192.0.2.10", "secret"]:
            self.assertNotIn(forbidden, combined)
        self.assertEqual(summary["outfiles"], [])
        self.assertEqual(summary["sysNames"], ["sys_b"])

    def test_functions_do_not_require_real_database_or_config_files(self):
        class MetadataService:
            def list_job_outfiles(self):
                return [("job_a", "outfile_a")]

            def list_result_table_sys_names(self):
                return [("dm.table_a", "sys_a")]

        summary = re_service.build_wide_table_lineage_summary(
            metadata_service=MetadataService()
        )

        self.assertEqual(summary["jobs"], ["JOB_A"])
        self.assertEqual(summary["resultTables"], ["DM.TABLE_A"])
        self.assertEqual(summary["recvPlans"], [])
        self.assertEqual(summary["sysNames"], ["sys_a"])
        self.assertEqual(summary["outfiles"], ["outfile_a"])


if __name__ == "__main__":
    unittest.main()
