import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.fine_runner import run_fine  # noqa: E402
from app.modules.audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


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
    def _build_context(self):
        saved_groups = []
        updates = []
        logs = []

        fine_rule = types.SimpleNamespace(
            rule_menu=lambda _path: (["/menu/demo"], "menu warn", 1),
            rule_authority=lambda _path, _menus: ("authority warn", 1),
            rule_fine=lambda _path: (
                "存在问题:\nbad dataset",
                1,
                ["ReportA", "connA", "spark", ["Sheet1"], ["dm.result_a", "src.input_a"]],
            ),
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

        context = WorkflowRuntimeContext(
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
            build_changes=lambda svn_result: [{"path": path} for path in svn_result["branch_changed_files"]],
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
            text_to_rows=lambda *_args, **_kwargs: [],
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
        self.assertEqual(report["reports"][0]["title"], "ReportA")
        self.assertEqual(report["reports"][0]["previewUrl"], "https://fine.example.com/svn_check.html?viewlet=ReportA")
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
            ],
        )
        self.assertEqual(report["refTables"], report["reports"][0]["refTables"])
        self.assertEqual(saved_groups[0]["fine"][0]["file"], "rel/report.cpt")

    def test_run_fine_uses_configured_preview_endpoint(self):
        context, *_ = self._build_context()

        with patch.dict("os.environ", {"FINE_REPORT_PREVIEW_URL": "http://10.133.6.11:4388/svn_check.html/"}):
            report = run_fine(context)

        self.assertEqual(
            report["reports"][0]["previewUrl"],
            "http://10.133.6.11:4388/svn_check.html?viewlet=ReportA",
        )


if __name__ == "__main__":
    unittest.main()
