import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.fine_runner import run_fine  # noqa: E402
from app.modules.audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


class FineRunnerContractTests(unittest.TestCase):
    def _context(self, *, loader=None, rule_fine=None):
        saved_groups = []
        logs = []

        mods = types.SimpleNamespace(
            fine_rule=types.SimpleNamespace(
                rule_menu=lambda _path: ([], "", 0),
                rule_authority=lambda _path, _menus: ("", 0),
                rule_fine=rule_fine or (lambda _path: ("", 0, ["ReportA", "", "", [], []])),
                get_cpt_sql=lambda _path: "",
            ),
            public_data=types.SimpleNamespace(
                all_para_table_lists=lambda: [],
                all_disabled_result_tables=lambda: [],
                all_result_table_sys_names=lambda: [],
            ),
            re_service=types.SimpleNamespace(
                get_filename=lambda path: Path(path).name,
                safe_remove_prefix=lambda path: path,
            ),
            load_registered_result_tables=loader or (lambda *, profile: set()),
        )

        def safe(label, fn, default):
            try:
                return fn()
            except Exception as exc:
                logs.append(f"{label}:{exc}")
                return default

        context = WorkflowRuntimeContext(
            mods=mods,
            workflow="fine-report",
            repo="svn://repo/fine/demo",
            task_id=9,
            ai_enabled=False,
            source_payload={
                "exported_paths": ["report.cpt"],
                "branch_changed_files": [],
                "trunk_conflict_files": [],
                "create_revision": "",
                "source_type": "svn",
                "workspace_root": "",
            },
            safe=safe,
            log=lambda msg, level="INFO": logs.append(f"{level}:{msg}"),
            update=lambda **_kwargs: None,
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
            build_svn_section=lambda _svn_result: {"branchChanged": [], "trunkConflict": []},
            build_changes=lambda _svn_result: [],
            build_conflicts=lambda _svn_result: [],
            build_lineage_summary=lambda *_args, **_kwargs: {},
            build_config_files=lambda _paths: [],
            build_job_table=lambda *_args, **_kwargs: None,
            build_ai=lambda _targets, _errors, _warnings: None,
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
        return context, saved_groups, logs

    def test_report_contract_keeps_source_payload_outside_top_level(self):
        context, saved_groups, _logs = self._context()

        report = run_fine(context)

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "menu",
                "authority",
                "reports",
                "refTables",
                "assetIssues",
                "unifiedAssetIssues",
                "metadataProfile",
            ],
        )
        self.assertEqual(report["metadataProfile"], "local_pg")
        self.assertEqual(report["task"]["sourceType"], "svn")
        self.assertEqual(report["task"]["workspaceRoot"], "")
        self.assertNotIn("source", report)
        self.assertNotIn("sourceType", report)
        self.assertNotIn("workspaceRoot", report)
        self.assertEqual(saved_groups[0], {"fine": []})

    def test_registered_table_loader_uses_active_profile_name(self):
        captured = {}

        def loader(*, profile):
            captured["profile"] = profile
            return set()

        context, _saved_groups, _logs = self._context(loader=loader)

        report = run_fine(context)

        self.assertEqual(report["task"]["status"], "pass")
        self.assertEqual(captured["profile"], "local_pg")

    def test_loader_failure_degrades_without_changing_report_shape(self):
        context, _saved_groups, logs = self._context(
            loader=lambda *, profile: (_ for _ in ()).throw(RuntimeError(f"boom:{profile}")),
            rule_fine=lambda _path: "fine rule fallback",
        )

        report = run_fine(context)

        self.assertEqual(report["task"]["status"], "warn")
        self.assertEqual(report["reports"][0]["issues"][0]["rule"], "规则执行异常")
        self.assertTrue(any("结果表登记库(lineage):boom:local_pg" in log for log in logs))


if __name__ == "__main__":
    unittest.main()
