import sys
import os
import types
import unittest
from unittest.mock import patch
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.workflows.fine_report.runner import run_fine  # noqa: E402
from app.modules.audit.shared.findings import CheckResult  # noqa: E402
from app.modules.audit.core.runtime import WorkflowRuntimeContext  # noqa: E402


class _FakeValues:
    def __init__(self, rows):
        self._rows = rows

    def tolist(self):
        return self._rows


class _FakeTable:
    def __init__(self, rows):
        self.values = _FakeValues(rows)

    def fillna(self, _value):
        return self

    def astype(self, _dtype):
        return self


class FineRunnerTests(unittest.TestCase):
    def setUp(self):
        self._environment = patch.dict(os.environ, {}, clear=True)
        self._environment.start()
        self.addCleanup(self._environment.stop)

    def _build_context(self):
        saved_groups = []
        updates = []
        logs = []

        menu_result = CheckResult(artifacts={"menu_entries": ["/menu/demo"]})
        menu_result.add("fine.menu.demo", "目录示例", "err", "menu warn")
        authority_result = CheckResult()
        authority_result.add("fine.authority.demo", "权限示例", "err", "authority warn")
        report_result = CheckResult(artifacts={
            "viewlet": "ReportA",
            "connection": "connA",
            "engine": "spark",
            "sheets": ["Sheet1"],
            "sql_tables": ["dm.result_a", "src.input_a", "tmp.stage_a"],
        })
        report_result.add("fine.report.demo", "数据集示例", "err", "bad dataset")
        fine_rule = types.SimpleNamespace(
            rule_menu=lambda _path: menu_result,
            rule_authority=lambda _path, _menus: authority_result,
            rule_fine=lambda _path: report_result,
            get_cpt_sql=lambda _path: "select * from dm.result_a",
        )
        public_data = types.SimpleNamespace(
            all_para_table_lists=lambda: [("src.input_a",)],
            all_disabled_result_tables=lambda: [("dm.result_a",)],
            all_result_table_sys_names=lambda: [("dm.result_a", "SYS_A")],
        )
        re_service = types.SimpleNamespace(
            load_txt_to_df=lambda _path, _cols: _FakeTable([["后台A", "前台A", "tab"]]),
            load_txt_to_df2=lambda _path, _cols: _FakeTable([["前台A", "ROLE_USER"]]),
            get_filename=lambda path: Path(path).name,
            safe_remove_prefix=lambda path: f"rel/{Path(path).name}",
        )
        mods = types.SimpleNamespace(
            fine_rule=fine_rule,
            public_data=public_data,
            re_service=re_service,
            load_registered_result_tables=lambda *, profile: {"DM.RESULT_A"},
        )

        def safe(label, fn, default):
            try:
                return fn()
            except Exception as exc:  # pragma: no cover - exercised in contract tests
                logs.append((label, str(exc)))
                return default

        context = WorkflowRuntimeContext.from_legacy(
            mods=mods,
            workflow="fine-report",
            repo="svn://repo/fine/demo",
            task_id=1,
            ai_enabled=False,
            source_payload={
                "exported_paths": ["menu.txt", "authority.txt", "report.cpt"],
                "branch_changed_files": ["report.cpt"],
                "trunk_conflict_files": [],
                "create_revision": "123",
                "source_type": "svn",
                "workspace_root": "C:/workspace/fine",
            },
            safe=safe,
            log=lambda msg, level="INFO": logs.append((level, msg)),
            update=lambda **kwargs: updates.append(kwargs),
            task_running=lambda *_args, **_kwargs: None,
            task_success=lambda *_args, **_kwargs: None,
            task_skipped=lambda *_args, **_kwargs: None,
            set_partial=lambda *_args, **_kwargs: None,
            save_category_rows=lambda rows: saved_groups.append(rows),
            download_url=lambda path: f"download://{Path(path).name}",
            build_task_meta=lambda svn_result, status, extra: {
                "status": status,
                "sourceType": svn_result["source_type"],
                "workspaceRoot": svn_result["workspace_root"],
                **extra,
            },
            build_svn_section=lambda svn_result: {
                "branchChanged": svn_result["branch_changed_files"],
                "trunkConflict": svn_result["trunk_conflict_files"],
            },
            build_changes=lambda svn_result: [
                {
                    "type": "M",
                    "path": path,
                    "cat": "report",
                    "downloadUrl": f"download://{Path(path).name}",
                }
                for path in svn_result["branch_changed_files"]
            ],
            build_conflicts=lambda svn_result: list(svn_result["trunk_conflict_files"]),
            build_lineage_summary=lambda *_args, **_kwargs: {},
            build_config_files=lambda _paths: [],
            build_job_table=lambda *_args, **_kwargs: None,
            build_ai=lambda targets, errors, warnings: {
                "targets": list(targets),
                "errors": errors,
                "warnings": warnings,
            },
            get_active_profile_name=lambda: "local_pg",
            collect_hcyt_input_files=lambda *_args, **_kwargs: None,
            build_source_classified_progress=lambda *_args, **_kwargs: None,
            publish_hcyt_progress=lambda *_args, **_kwargs: None,
            run_hcyt_rules=lambda *_args, **_kwargs: None,
            run_hcyt_inspections=lambda *_args, **_kwargs: None,
            run_hcyt_ai_review=lambda *_args, **_kwargs: None,
            sync_hcyt_legacy_results=lambda *_args, **_kwargs: None,
            build_hcyt_report=lambda *_args, **_kwargs: None,
            run_hcyt_schedule=lambda *_args, **_kwargs: None,
            run_hcyt_programs=lambda *_args, **_kwargs: None,
            status_of=lambda errors, warnings: "fail" if errors else ("warn" if warnings else "pass"),
            count_levels=lambda _rows: (0, 0),
        )
        return context, saved_groups, updates, logs

    def test_run_fine_preserves_menu_authority_and_template_sections(self):
        context, saved_groups, updates, _logs = self._build_context()

        report = run_fine(context)

        self.assertEqual([update["progress"] for update in updates], [40, 55])
        self.assertEqual(report["menu"]["columns"], ["后台目录", "前台目录", "预览方式"])
        self.assertEqual(report["menu"]["rows"], [["后台A", "前台A", "tab"]])
        self.assertEqual(report["authority"]["columns"], ["前台目录", "赋予权限"])
        self.assertEqual(report["authority"]["rows"], [["前台A", "ROLE_USER"]])
        self.assertEqual(report["task"]["reports"], len(report["reports"]))
        self.assertEqual(len(report["reports"]), 1)
        self.assertEqual(report["reports"][0]["title"], "ReportA")
        self.assertEqual(report["reports"][0]["previewUrl"], "https://fine.example.com/fine/svn_check.html?viewlet=ReportA")
        self.assertEqual(
            report["changes"],
            [{"type": "M", "path": "report.cpt", "cat": "report", "downloadUrl": "download://report.cpt"}],
        )
        self.assertEqual(report["reports"][0]["downloadUrl"], report["changes"][0]["downloadUrl"])
        self.assertEqual(
            report["reports"][0]["datasets"],
            [{"name": "数据集 SQL", "sql": "select * from dm.result_a", "rows": "-"}],
        )
        self.assertEqual(
            report["reports"][0]["refTables"],
            [
                {
                    "name": "DM.RESULT_A",
                    "type": "result",
                    "disabled": True,
                    "sysNames": ["SYS_A"],
                    "highlight": True,
                },
                {
                    "name": "SRC.INPUT_A",
                    "type": "src",
                    "disabled": False,
                    "sysNames": [],
                    "highlight": False,
                },
                {
                    "name": "TMP.STAGE_A",
                    "type": "mid",
                    "disabled": False,
                    "sysNames": [],
                    "highlight": False,
                },
            ],
        )
        self.assertEqual(report["refTables"], report["reports"][0]["refTables"])
        self.assertEqual(
            len(saved_groups[0]["fine"]),
            sum(len(item["issues"]) for item in report["reports"]),
        )
        self.assertEqual(saved_groups[0]["fine"][0]["file"], "rel/report.cpt")

    def test_run_fine_only_highlights_disabled_or_configured_source_system_tables(self):
        context, *_ = self._build_context()
        context.services.mods.fine_rule.rule_fine = lambda _path: CheckResult(artifacts={
            "viewlet": "ReportA",
            "connection": "",
            "engine": "",
            "sheets": [],
            "sql_tables": [
                "dwf.f_ordinary",
                "dwf.f_configured",
                "dwf.f_disabled",
                "dwm.m_normal",
            ],
        })
        context.services.mods.load_registered_result_tables = lambda *, profile: {
            "DWF.F_ORDINARY",
            "DWF.F_CONFIGURED",
            "DWF.F_DISABLED",
            "DWM.M_NORMAL",
        }
        context.services.mods.public_data.all_disabled_result_tables = lambda: [("dwf.f_disabled",)]
        context.services.mods.public_data.all_result_table_sys_names = lambda: [
            ("dwf.f_ordinary", "核心系统"),
            ("dwf.f_ordinary", "核心系统"),
            ("dwf.f_configured", "普通系统"),
            ("DWF.F_CONFIGURED", "CONFIG_SYS"),
        ]
        configured_rules = {
            "display": {"highlight_result_source_systems": ["CONFIG_SYS"]},
            "fine_report": {
                "file_conventions": {
                    "template_extensions": [".cpt", ".frm"],
                    "menu_filename": "menu.txt",
                    "authority_filename": "authority.txt",
                }
            },
        }

        with patch(
            "app.modules.audit.workflows.fine_report.runner.get_audit_rules",
            return_value=configured_rules,
        ):
            report = run_fine(context)

        tables = {item["name"]: item for item in report["reports"][0]["refTables"]}
        self.assertEqual(
            tables["DWF.F_ORDINARY"],
            {
                "name": "DWF.F_ORDINARY",
                "type": "result",
                "disabled": False,
                "sysNames": ["核心系统"],
                "highlight": False,
            },
        )
        self.assertEqual(tables["DWF.F_CONFIGURED"]["sysNames"], ["普通系统", "CONFIG_SYS"])
        self.assertTrue(tables["DWF.F_CONFIGURED"]["highlight"])
        self.assertTrue(tables["DWF.F_DISABLED"]["highlight"])
        self.assertFalse(tables["DWM.M_NORMAL"]["highlight"])

    def test_run_fine_uses_configured_preview_endpoint(self):
        context, *_ = self._build_context()

        with patch.dict("os.environ", {"FINE_REPORT_PREVIEW_URL": "https://reports.example.test/fine/svn_check.html/"}):
            report = run_fine(context)

        self.assertEqual(
            report["reports"][0]["previewUrl"],
                "https://reports.example.test/fine/svn_check.html?viewlet=ReportA",
        )

    def test_run_fine_encodes_chinese_viewlet_path(self):
        context, *_ = self._build_context()
        context.services.mods.fine_rule.rule_fine = lambda _path: CheckResult(artifacts={
            "viewlet": r"数据仓库\数字金融部\信贷新老表对比.cpt",
            "connection": "",
            "engine": "",
            "sheets": [],
            "sql_tables": [],
        })

        with patch.dict("os.environ", {"FINE_REPORT_PREVIEW_URL": "https://reports.example.test/fine/svn_check.html"}):
            report = run_fine(context)

        self.assertEqual(
            report["reports"][0]["previewUrl"],
                "https://reports.example.test/fine/svn_check.html"
            "?viewlet=%E6%95%B0%E6%8D%AE%E4%BB%93%E5%BA%93%2F%E6%95%B0%E5%AD%97%E9%87%91%E8%9E%8D%E9%83%A8"
            "%2F%E4%BF%A1%E8%B4%B7%E6%96%B0%E8%80%81%E8%A1%A8%E5%AF%B9%E6%AF%94.cpt",
        )


if __name__ == "__main__":
    unittest.main()
