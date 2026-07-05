import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "backend" / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

from services import audit_metadata_service as service  # noqa: E402
from core import public_data  # noqa: E402


class RowLike:
    def __init__(self, **values):
        self._mapping = values


class AuditMetadataServiceTests(unittest.TestCase):
    def test_single_column_normalizer_handles_common_row_shapes(self):
        rows = [
            (" term_a ",),
            {"root_code": "term_b"},
            RowLike(root_code="term_d"),
            None,
            ("",),
            ("TERM_A",),
            {"root_code": " term_b "},
            "term_c",
            (None,),
        ]

        self.assertEqual(
            service._normalize_single_column_rows(rows),
            [("TERM_A",), ("TERM_B",), ("TERM_D",), ("TERM_C",)],
        )

    def test_single_column_normalizer_can_preserve_case_when_requested(self):
        rows = [(" view_a ",), ("VIEW_A",), {"table_name": "view_a"}]

        self.assertEqual(
            service._normalize_single_column_rows(rows, upper=False),
            [("view_a",), ("VIEW_A",)],
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
            self.assertEqual(service.list_view_names(), [])
            self.assertEqual(service.list_function_names(), [])
            self.assertEqual(service.list_para_table_names(), [])
            self.assertEqual(service.list_job_outfiles(), [])
            self.assertEqual(service.list_result_table_recv_details(), [])

    def test_lightweight_metadata_queries_parse_tuple_rows(self):
        sample_rows = [(" table_a ",), (None,), ("",), ("TABLE_A",), ("table_b",)]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_term_roots(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(service.list_view_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(service.list_function_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(service.list_para_table_names(), [("TABLE_A",), ("TABLE_B",)])

    def test_lightweight_metadata_queries_parse_dict_rows(self):
        sample_rows = [
            {"root_code": " root_a "},
            {"root_code": None},
            {"root_code": ""},
            {"root_code": "ROOT_A"},
            {"root_code": "root_b"},
        ]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_term_roots(), [("ROOT_A",), ("ROOT_B",)])
            self.assertEqual(service.list_view_names(), [("ROOT_A",), ("ROOT_B",)])
            self.assertEqual(service.list_function_names(), [("ROOT_A",), ("ROOT_B",)])
            self.assertEqual(service.list_para_table_names(), [("ROOT_A",), ("ROOT_B",)])

    def test_lightweight_metadata_queries_parse_row_like_rows(self):
        sample_rows = [RowLike(name=" item_a "), RowLike(name="ITEM_A"), RowLike(name="item_b")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_term_roots(), [("ITEM_A",), ("ITEM_B",)])
            self.assertEqual(service.list_view_names(), [("ITEM_A",), ("ITEM_B",)])
            self.assertEqual(service.list_function_names(), [("ITEM_A",), ("ITEM_B",)])
            self.assertEqual(service.list_para_table_names(), [("ITEM_A",), ("ITEM_B",)])

    def test_other_metadata_list_functions_keep_legacy_compatible_tuple_shapes(self):
        sample_rows = [("table_a", "plan_a", "sys_a")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_job_outfiles(), [("table_a", "plan_a")])
            self.assertEqual(service.list_result_table_recv_details(), [("table_a", "plan_a", "sys_a")])

    def test_public_data_lightweight_wrappers_remain_callable(self):
        sample_rows = [("table_a",), ("TABLE_A",), ("table_b",)]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(public_data.all_term_roots(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(public_data.all_view_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(public_data.all_function_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(public_data.all_para_table_lists(), [("TABLE_A",), ("TABLE_B",)])

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
        for forbidden in ["dsn", "jdbc", "password", "token", "192.0.2.10", "secret", "real_user"]:
            self.assertNotIn(forbidden, log_text)
        self.assertIn("profile=", log_text)
        self.assertIn("backend=gaussdb", log_text)
        self.assertIn("function=list_term_roots", log_text)
        self.assertIn("error=runtimeerror", log_text)


if __name__ == "__main__":
    unittest.main()
