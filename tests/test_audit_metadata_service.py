import logging
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.metadata.services import audit_metadata_service as service  # noqa: E402
from app.modules.metadata.services import db_service as db_service  # noqa: E402
from app.modules.metadata.services import public_data  # noqa: E402
from app.db.metadata.compat import router  # noqa: E402
from app.db.profiles import DatabaseProfile  # noqa: E402
from scripts import init_pg  # noqa: E402


class RowLike:
    def __init__(self, **values):
        self._mapping = values


class AttrRow:
    def __init__(self, **values):
        for name, value in values.items():
            setattr(self, name, value)


class AuditMetadataServiceTests(unittest.TestCase):
    def setUp(self):
        service._term_root_memory_cache = None

    def test_metadata_path_owns_implementation(self):
        self.assertIs(service.db_router, router)
        self.assertTrue(callable(db_service.select_sql))

    def test_db_service_defaults_to_metadata_profile(self):
        with patch.object(db_service, "get_metadata_profile", return_value=MagicMock(name="profile", name_attr="ignored")) as resolver:
            resolver.return_value.name = "local_pg"
            with patch.object(db_service, "select_sql_with_profile", return_value=[("ok",)]) as select:
                self.assertEqual(db_service.select_sql("select 1"), [("ok",)])
        select.assert_called_once_with("local_pg", "select 1")

    def test_audit_metadata_service_routes_explicit_metadata_profile(self):
        with patch.object(service.db_router, "get_backend", return_value="postgresql"):
            with patch.object(service.db_router, "select_sql_with_profile", return_value=[]) as select:
                service.list_job_outfiles("local_pg")
        self.assertEqual(select.call_args.args[0], "local_pg")

    def test_metadata_init_uses_new_sql_path_without_changing_schema(self):
        new_sql_path = BACKEND_DIR / "app" / "modules" / "metadata" / "init" / "postgres_schema.sql"

        self.assertEqual(init_pg.SCHEMA_SQL, new_sql_path)
        self.assertTrue(new_sql_path.is_file())

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
            (" table_a ", "outfile_a"),
        ]

        self.assertEqual(
            service._normalize_multi_column_rows(rows, (("table",), ("outfile",))),
            [
                ("table_a", "outfile_a"),
                ("table_b", "outfile_b"),
                ("table_c", ""),
            ],
        )

    def test_metadata_queries_degrade_to_empty_lists_on_router_failure(self):
        list_functions = [
            service.list_view_names,
            service.list_function_names,
            service.list_para_table_names,
            service.list_job_outfiles,
            service.list_upstream_system_ids,
            service.list_result_table_sys_names,
        ]

        with patch.object(service.db_router, "select_sql_with_profile", side_effect=RuntimeError("boom")):
            for list_function in list_functions:
                with self.subTest(function=list_function.__name__):
                    self.assertEqual(list_function(), [])

    def test_metadata_queries_degrade_to_empty_lists_when_router_returns_none(self):
        with patch.object(service.db_router, "select_sql_with_profile", return_value=None):
            self.assertEqual(service.list_view_names(), [])
            self.assertEqual(service.list_function_names(), [])
            self.assertEqual(service.list_para_table_names(), [])
            self.assertEqual(service.list_job_outfiles(), [])
            self.assertEqual(service.list_upstream_system_ids(), [])
            self.assertEqual(service.list_result_table_sys_names(), [])

    def test_lightweight_metadata_queries_parse_tuple_rows(self):
        sample_rows = [(" table_a ",), (None,), ("",), ("TABLE_A",), ("table_b",)]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
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
            self.assertEqual(service.list_view_names(), [("ROOT_A",), ("ROOT_B",)])
            self.assertEqual(service.list_function_names(), [("ROOT_A",), ("ROOT_B",)])
            self.assertEqual(service.list_para_table_names(), [("ROOT_A",), ("ROOT_B",)])

    def test_lightweight_metadata_queries_parse_row_like_rows(self):
        sample_rows = [RowLike(name=" item_a "), RowLike(name="ITEM_A"), RowLike(name="item_b")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_view_names(), [("ITEM_A",), ("ITEM_B",)])
            self.assertEqual(service.list_function_names(), [("ITEM_A",), ("ITEM_B",)])
            self.assertEqual(service.list_para_table_names(), [("ITEM_A",), ("ITEM_B",)])

    def test_other_metadata_list_functions_keep_compatible_tuple_shapes(self):
        sample_rows = [("table_a", "system_a")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_job_outfiles(), [("table_a", "system_a")])
            self.assertEqual(service.list_result_table_sys_names(), [("table_a", "system_a")])

    def test_p0_5c_queries_parse_tuple_rows_and_clean_values(self):
        sample_rows = [
            (" table_a ", " value_a ", " sys_a "),
            ("table_a", "value_a", "sys_a"),
            (None, "", None),
            ("table_b",),
        ]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_job_outfiles(), [("table_a", "value_a"), ("table_b", "")])
            self.assertEqual(service.list_upstream_system_ids(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(
                service.list_result_table_sys_names(),
                [("table_a", "value_a"), ("table_b", "")],
            )

    def test_result_table_source_system_query_uses_exact_left_join(self):
        self.assertIn("dwp.p_field_mapping_table", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertIn("dwp.p_upstream_system", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertIn("u.system_pk = t.upstream_system_id", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertIn("LEFT JOIN", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertNotIn("is_deleted", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertNotIn("DISTINCT", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertNotIn("ORDER BY", service.RESULT_TABLE_SYS_NAME_SQL)
        self.assertNotIn("TRIM", service.RESULT_TABLE_SYS_NAME_SQL)

        with patch.object(
            service.db_router,
            "select_sql_with_profile",
            return_value=[
                ("DWF.F_EVT_COMC_HOLIDAY", "核心系统"),
                ("DWF.F_PTY_COM_INFO", "老信贷系统"),
                ("DWF.F_PTY_COM_INFO", "核心系统"),
                ("DWF.F_PTY_COM_INFO", "老信贷系统"),
            ],
        ):
            self.assertEqual(
                service.list_result_table_sys_names(),
                [
                    ("DWF.F_EVT_COMC_HOLIDAY", "核心系统"),
                    ("DWF.F_PTY_COM_INFO", "老信贷系统"),
                    ("DWF.F_PTY_COM_INFO", "核心系统"),
                ],
            )

    def test_upstream_system_id_query_uses_only_active_records(self):
        self.assertIn("SELECT system_id", service.UPSTREAM_SYSTEM_ID_SQL)
        self.assertIn("FROM dwp.p_upstream_system", service.UPSTREAM_SYSTEM_ID_SQL)
        self.assertIn("WHERE is_deleted = 'N'", service.UPSTREAM_SYSTEM_ID_SQL)

        with patch.object(
            service.db_router,
            "select_sql_with_profile",
            return_value=[(" plan_a ",), {"system_id": "PLAN_A"}, RowLike(system_id="plan_b")],
        ):
            self.assertEqual(service.list_upstream_system_ids(), [("PLAN_A",), ("PLAN_B",)])

    def test_p0_5c_queries_parse_dict_rows_by_field_name(self):
        sample_rows = [
            {
                "ignored": "wrong",
                "job_name": " job_a ",
                "outfile": " outfile_a ",
                "recv_plan": " plan_a ",
                "system_id": " plan_a ",
                "table_name": " table_a ",
                "sys_name": " sys_a ",
            },
            {
                "ignored": "wrong",
                "a": "job_b",
                "b": "outfile_b",
                "result_table": "table_b",
                "source_system": "sys_b",
                "plan": "plan_b",
                "system_id": "plan_b",
            },
        ]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_job_outfiles(), [("job_a", "outfile_a"), ("job_b", "outfile_b")])
            self.assertEqual(service.list_upstream_system_ids(), [("PLAN_A",), ("PLAN_B",)])
            self.assertEqual(service.list_result_table_sys_names(), [("table_a", "sys_a"), ("table_b", "sys_b")])

    def test_p0_5c_queries_parse_row_like_and_attr_rows(self):
        sample_rows = [
            RowLike(job_name=" job_a ", outfile=" outfile_a ", table_name=" table_a ", recv_plan=" plan_a ", system_id=" plan_a ", sys_name=" sys_a "),
            AttrRow(job_name="job_b", outfile="outfile_b", table_name="table_b", recv_plan="plan_b", system_id="plan_b", sys_name="sys_b"),
        ]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(service.list_job_outfiles(), [("job_a", "outfile_a"), ("job_b", "outfile_b")])
            self.assertEqual(service.list_upstream_system_ids(), [("PLAN_A",), ("PLAN_B",)])
            self.assertEqual(service.list_result_table_sys_names(), [("table_a", "sys_a"), ("table_b", "sys_b")])

    def test_public_data_lightweight_wrappers_remain_callable(self):
        sample_rows = [("table_a",), ("TABLE_A",), ("table_b",)]

        with patch.object(service, "_fetch_asset_portal_term_roots", return_value=[("ROOT_A",), ("root_b",)]):
            self.assertEqual(public_data.all_term_roots(), [("ROOT_A",), ("root_b",)])
        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(public_data.all_view_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(public_data.all_function_names(), [("TABLE_A",), ("TABLE_B",)])
            self.assertEqual(public_data.all_para_table_lists(), [("TABLE_A",), ("TABLE_B",)])

    def test_public_data_p0_5c_wrappers_remain_callable(self):
        sample_rows = [("table_a", "plan_a", "sys_a")]

        with patch.object(service.db_router, "select_sql_with_profile", return_value=sample_rows):
            self.assertEqual(public_data.all_job_outfile(), [("table_a", "plan_a")])
            self.assertEqual(public_data.all_upstream_system_ids(), [("TABLE_A",)])
            self.assertEqual(public_data.all_result_table_sys_names(), [("table_a", "plan_a")])

    def test_partition_counts_use_index_friendly_grouped_catalog_predicates(self):
        dws_profile = DatabaseProfile("inner_dws", "dws", {"metadata": {"partition_catalog": True}})
        with patch.object(public_data, "get_metadata_profile", return_value=dws_profile), patch.object(
            public_data,
            "select_sql",
            return_value=[("DWPURR", "TABLE_A", 3), ("DWPURR", "TABLE_B", 1)],
        ) as select_sql:
            result = public_data.all_tab_partition_counts([
                "dwpurr.table_a",
                "DWPURR.TABLE_B",
                "DWPURR.TABLE_A",
                "invalid",
            ])

        self.assertEqual(result, {"DWPURR.TABLE_A": 3, "DWPURR.TABLE_B": 1})
        sql = select_sql.call_args.args[0]
        self.assertIn("SCHEMA IN ('DWPURR', 'dwpurr')", sql)
        self.assertIn("TABLE_NAME IN ('TABLE_A', 'TABLE_B', 'table_a', 'table_b')", sql)
        self.assertIn("GROUP BY upper(SCHEMA), upper(TABLE_NAME)", sql)
        where_clause = sql.split("WHERE", 1)[1].split("GROUP BY", 1)[0]
        self.assertNotIn("upper(", where_clause.lower())

    def test_partition_counts_keep_zero_for_unreturned_valid_tables(self):
        dws_profile = DatabaseProfile("inner_dws", "dws", {"metadata": {"partition_catalog": True}})
        with patch.object(public_data, "get_metadata_profile", return_value=dws_profile), patch.object(public_data, "select_sql", return_value=[]):
            result = public_data.all_tab_partition_counts(["DWPURR.TABLE_A"])

        self.assertEqual(result, {"DWPURR.TABLE_A": 0})

    def test_partition_queries_fall_back_from_local_mirror_to_runtime_dws(self):
        metadata = DatabaseProfile("local_pg", "postgresql", {"metadata": {"partition_catalog": False}})
        runtime = DatabaseProfile("inner_dws", "dws", {"metadata": {"partition_catalog": True}})
        with patch.object(public_data, "get_metadata_profile", return_value=metadata), patch.object(
            public_data, "get_active_profile", return_value=runtime
        ), patch.object(public_data, "select_sql", return_value=[(2,)]) as select:
            with self.assertLogs("svn_check.partition_metadata", level=logging.INFO) as logs:
                result = public_data.all_tab_partitions("DWP.TABLE_A")
        self.assertEqual(result, [(2,)])
        self.assertEqual(select.call_args.kwargs["profile"], "inner_dws")
        log_text = "\n".join(logs.output)
        self.assertIn("metadata_profile=local_pg", log_text)
        self.assertIn("query_profile=inner_dws", log_text)
        self.assertIn("fallback=True", log_text)

    def test_partition_queries_fail_closed_when_no_catalog_is_available(self):
        local = DatabaseProfile("local_pg", "postgresql", {"metadata": {"partition_catalog": False}})
        with patch.object(public_data, "get_metadata_profile", return_value=local), patch.object(
            public_data, "get_active_profile", return_value=local
        ), patch.object(public_data, "select_sql") as select:
            with self.assertRaisesRegex(RuntimeError, "partition metadata catalog is unavailable"):
                public_data.all_tab_partitions("DWP.TABLE_A")
        select.assert_not_called()

    def test_catalog_metadata_filters_leave_indexed_columns_unwrapped(self):
        self.assertIn(
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema')",
            service.VIEW_NAME_SQL,
        )
        self.assertIn(
            "WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')",
            service.FUNCTION_NAME_SQL,
        )

    def test_degraded_log_excludes_sensitive_exception_text(self):
        sensitive_message = (
            "dsn=jdbc:postgresql://192.0.2.10/demo "
            "password=secret token=abc user=real_user"
        )

        with patch.object(service.db_router, "get_backend", return_value="gaussdb"):
            with patch.object(service.db_router, "select_sql_with_profile", side_effect=RuntimeError(sensitive_message)):
                with self.assertLogs("svn_check.audit_metadata", level=logging.WARNING) as logs:
                    self.assertEqual(service.list_view_names(), [])

        log_text = "\n".join(logs.output).lower()
        for forbidden in ["dsn", "jdbc", "password", "token", "192.0.2.10", "secret", "real_user"]:
            self.assertNotIn(forbidden, log_text)
        self.assertIn("profile=", log_text)
        self.assertIn("backend=gaussdb", log_text)
        self.assertIn("function=list_view_names", log_text)
        self.assertIn("error=runtimeerror", log_text)

    @patch.dict(os.environ, {"ASSET_PORTAL_BASE_URL": "https://asset.example.test/", "ASSET_PORTAL_API_TOKEN": "test-token"}, clear=True)
    def test_term_roots_are_read_from_asset_portal_api(self):
        response = MagicMock()
        response.read.return_value = json.dumps({"items": [{"abbr": "acct"}, {"abbr": "AMT"}, {"abbr": "acct"}]}).encode("utf-8")
        response.__enter__.return_value = response

        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(service.list_term_roots(), [("ACCT",), ("AMT",)])

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://asset.example.test/api/roots")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    @patch.dict(os.environ, {"ASSET_PORTAL_BASE_URL": "https://asset.example.test"}, clear=True)
    def test_term_roots_fall_back_to_persistent_snapshot_when_api_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = Path(tmp) / "roots.json"
            cache_file.write_text('{"roots": ["acct", "amt"]}', encoding="utf-8")
            with patch.dict(os.environ, {"ASSET_PORTAL_ROOT_CACHE_FILE": str(cache_file)}, clear=False):
                with patch("urllib.request.urlopen", side_effect=OSError("offline")):
                    self.assertEqual(service.list_term_roots(), [("ACCT",), ("AMT",)])

    @patch.dict(os.environ, {"ASSET_PORTAL_BASE_URL": "https://asset.example.test"}, clear=True)
    def test_term_roots_write_snapshot_after_successful_api_fetch(self):
        response = MagicMock()
        response.read.return_value = b'{"items": [{"abbr": "acct"}]}'
        response.__enter__.return_value = response
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = Path(tmp) / "roots.json"
            with patch.dict(os.environ, {"ASSET_PORTAL_ROOT_CACHE_FILE": str(cache_file)}, clear=False):
                with patch("urllib.request.urlopen", return_value=response):
                    self.assertEqual(service.list_term_roots(), [("ACCT",)])
            self.assertEqual(json.loads(cache_file.read_text(encoding="utf-8")), {"roots": ["ACCT"]})


if __name__ == "__main__":
    unittest.main()
