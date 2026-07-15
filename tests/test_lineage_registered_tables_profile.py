import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.modules.audit.engine as audit_engine  # noqa: E402
from app.modules.lineage import mapping_compat as mapping_sqlite  # noqa: E402


class RegisteredTablesProfileRoutingTests(unittest.TestCase):
    def setUp(self):
        self.previous_mods = audit_engine._mods

    def tearDown(self):
        audit_engine._mods = self.previous_mods

    def _new_run(self, workflow="fine-report", repo="svn://repo/fine/demo"):
        run = audit_engine.TaskRun.__new__(audit_engine.TaskRun)
        run.task_id = 1
        run.repo = repo
        run.workflow = workflow
        run.ai_enabled = False
        run.debug_enabled = False
        run.author = "tester"
        run.source_type = "svn"
        run.logs = []
        run.start_ts = 0
        run.update = lambda *args, **kwargs: None
        run.save_category_rows = lambda *args, **kwargs: None
        return run

    def test_load_registered_result_tables_defaults_to_czcb_profile(self):
        captured = {}

        def fake_select(profile, sql):
            captured["profile"] = profile
            captured["sql"] = sql
            return [(" dm.table_a ",)]

        with patch.object(mapping_sqlite, "select_sql_with_profile", side_effect=fake_select):
            result = mapping_sqlite.load_registered_result_tables()

        self.assertEqual(captured["profile"], "czcb")
        self.assertIn("FROM dwp.p_job_hjj", captured["sql"])
        self.assertEqual(result, {"DM.TABLE_A"})

    def test_hcyt_registered_result_tables_uses_active_profile(self):
        captured = {}

        def fake_load_registered_result_tables(*, profile):
            captured["profile"] = profile
            return set()

        public_data = types.SimpleNamespace(
            all_para_table_lists=lambda: [],
            all_disabled_result_tables=lambda: [],
            all_result_table_sys_names=lambda: [],
            all_job=lambda: [],
        )
        re_service = types.SimpleNamespace(
            get_filename=lambda path: Path(path).name,
            read_data_from_file=lambda _path: "",
            safe_remove_prefix=lambda path: path,
            build_export_download_url=lambda _path: "",
        )
        hcyt = types.SimpleNamespace(
            rule_dws_py=lambda _path: ("", "", 0, []),
            get_program_table_name=lambda _path: "",
        )
        audit_engine._mods = types.SimpleNamespace(
            load_registered_result_tables=fake_load_registered_result_tables,
            public_data=public_data,
            re_service=re_service,
            hcyt=hcyt,
            hcyt_python_rule=types.SimpleNamespace(build_asset_table_review_issues=lambda *_args, **_kwargs: []),
            hcyt_ddl_rule=types.SimpleNamespace(collect_root_missing_issues=lambda *_args, **_kwargs: []),
        )

        run = self._new_run(workflow="hcyt", repo="svn://repo/hcyt/demo")
        with patch.object(audit_engine, "get_active_profile", return_value=types.SimpleNamespace(name="local_pg")):
            run.run_hcyt_programs(["/tmp/demo.py"], None, None, None)

        self.assertEqual(captured["profile"], "local_pg")

    def test_fine_registered_result_tables_uses_active_profile(self):
        captured = {}

        def fake_load_registered_result_tables(*, profile):
            captured["profile"] = profile
            return set()

        public_data = types.SimpleNamespace(
            all_para_table_lists=lambda: [],
            all_disabled_result_tables=lambda: [],
            all_result_table_sys_names=lambda: [],
        )
        re_service = types.SimpleNamespace(
            get_filename=lambda path: Path(path).name,
            safe_remove_prefix=lambda path: path,
            build_export_download_url=lambda _path: "",
        )
        fine_rule = types.SimpleNamespace()
        audit_engine._mods = types.SimpleNamespace(
            load_registered_result_tables=fake_load_registered_result_tables,
            public_data=public_data,
            re_service=re_service,
            fine_rule=fine_rule,
            call_sql_llm=lambda _path: None,
        )

        run = self._new_run()
        svn_result = {
            "exported_paths": [],
            "branch_changed_files": [],
            "trunk_conflict_files": [],
            "create_revision": "",
            "source_type": "svn",
            "workspace_root": "",
        }

        with patch.dict(os.environ, {"CODE_AUDIT_DB_PROFILE": "local_pg"}, clear=False):
            with patch.object(audit_engine, "get_active_profile", return_value=types.SimpleNamespace(name="local_pg")):
                report = run.run_fine(svn_result)

        self.assertEqual(report["task"]["status"], "pass")
        self.assertEqual(captured["profile"], "local_pg")

    def test_fine_registered_result_tables_loader_failure_is_still_soft_failed(self):
        public_data = types.SimpleNamespace(
            all_para_table_lists=lambda: [],
            all_disabled_result_tables=lambda: [],
            all_result_table_sys_names=lambda: [],
        )
        re_service = types.SimpleNamespace(
            get_filename=lambda path: Path(path).name,
            safe_remove_prefix=lambda path: path,
            build_export_download_url=lambda _path: "",
        )
        audit_engine._mods = types.SimpleNamespace(
            load_registered_result_tables=lambda *, profile: (_ for _ in ()).throw(RuntimeError(f"boom:{profile}")),
            public_data=public_data,
            re_service=re_service,
            fine_rule=types.SimpleNamespace(),
            call_sql_llm=lambda _path: None,
        )

        run = self._new_run()
        svn_result = {
            "exported_paths": [],
            "branch_changed_files": [],
            "trunk_conflict_files": [],
            "create_revision": "",
            "source_type": "svn",
            "workspace_root": "",
        }

        with patch.object(audit_engine, "get_active_profile", return_value=types.SimpleNamespace(name="local_pg")):
            report = run.run_fine(svn_result)

        self.assertEqual(report["task"]["status"], "pass")
        self.assertTrue(any("结果表登记库(lineage)" in log["msg"] for log in run.logs))


if __name__ == "__main__":
    unittest.main()
