import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "backend" / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

from services import audit_metadata_service as service  # noqa: E402


class AuditMetadataServiceTests(unittest.TestCase):
    def test_single_column_normalizer_handles_common_row_shapes(self):
        rows = [
            (" term_a ",),
            {"root_code": "term_b"},
            None,
            ("",),
            "term_c",
            (None,),
        ]

        self.assertEqual(
            service._normalize_single_column_rows(rows),
            [("TERM_A",), ("TERM_B",), ("TERM_C",)],
        )

    def test_multi_column_normalizer_keeps_stable_tuple_width(self):
        rows = [
            (" table_a ", " outfile_a "),
            {"table": "table_b", "outfile": "outfile_b"},
            (None, ""),
            ("table_c",),
        ]

        self.assertEqual(
            service._normalize_multi_column_rows(rows, 2),
            [
                ("table_a", "outfile_a"),
                ("table_b", "outfile_b"),
                ("table_c", ""),
            ],
        )

    def test_metadata_queries_degrade_to_empty_lists_on_router_failure(self):
        list_functions = [
            service.list_term_roots,
            service.list_view_names,
            service.list_function_names,
            service.list_para_table_names,
            service.list_job_outfiles,
            service.list_recv_mapping_plans,
            service.list_result_table_sys_names,
            service.list_result_table_recv_details,
        ]

        with patch.object(service.db_router, "select_sql_with_profile", side_effect=RuntimeError("boom")):
            for list_function in list_functions:
                with self.subTest(function=list_function.__name__):
                    self.assertEqual(list_function(), [])

    def test_metadata_queries_degrade_to_empty_lists_when_router_returns_none(self):
        with patch.object(service.db_router, "select_sql_with_profile", return_value=None):
            self.assertEqual(service.list_term_roots(), [])
            self.assertEqual(service.list_job_outfiles(), [])
            self.assertEqual(service.list_result_table_recv_details(), [])

    def test_list_functions_return_legacy_compatible_tuple_shapes(self):
        sample_rows = [("table_a", "plan_a", "sys_a")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_term_roots(), [("TABLE_A",)])
            self.assertEqual(service.list_job_outfiles(), [("table_a", "plan_a")])
            self.assertEqual(service.list_result_table_recv_details(), [("table_a", "plan_a", "sys_a")])

    def test_degraded_log_excludes_sensitive_exception_text(self):
        sensitive_message = (
            "dsn=jdbc:postgresql://192.0.2.10/demo "
            "password=secret token=abc user=real_user"
        )

        with patch.object(service.db_router, "get_backend", return_value="gaussdb"):
            with patch.object(service.db_router, "select_sql_with_profile", side_effect=RuntimeError(sensitive_message)):
                with self.assertLogs("svn_check.audit_metadata", level=logging.WARNING) as logs:
                    self.assertEqual(service.list_term_roots(), [])

        log_text = "\n".join(logs.output).lower()
        for forbidden in ["dsn", "password", "token", "192.0.2.10", "secret", "real_user"]:
            self.assertNotIn(forbidden, log_text)
        self.assertIn("profile=", log_text)
        self.assertIn("backend=gaussdb", log_text)
        self.assertIn("function=list_term_roots", log_text)
        self.assertIn("error=runtimeerror", log_text)


if __name__ == "__main__":
    unittest.main()
