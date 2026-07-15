import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_runner import run_hcyt  # noqa: E402
from app.modules.audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


class _InputFiles:
    def as_run_inputs(self):
        grouped = {"dws": [], "hive": [], "python": [], "sbin": [], "config": [], "recv": []}
        return (
            None,
            None,
            [],
            [],
            [],
            [],
            [],
            [],
            None,
            None,
            None,
            None,
            None,
            grouped,
            [],
            [],
        )


class HcytRunnerContractTests(unittest.TestCase):
    def _context(self):
        partials = {}
        task_events = []
        saved_groups = []

        return (
            WorkflowRuntimeContext(
                mods=types.SimpleNamespace(re_service=types.SimpleNamespace(), hcyt=types.SimpleNamespace()),
                workflow="hcyt",
                repo="svn://repo/hcyt/demo",
                task_id=10,
                ai_enabled=False,
                source_payload={
                    "exported_paths": [],
                    "branch_changed_files": [],
                    "trunk_conflict_files": [],
                    "create_revision": "",
                    "source_type": "local",
                    "workspace_root": "C:/workspace",
                },
                safe=lambda _label, fn, _default: fn(),
                log=lambda *_args, **_kwargs: None,
                update=lambda **_kwargs: None,
                task_running=lambda key: task_events.append(("running", key)),
                task_success=lambda key, **kwargs: task_events.append(("success", key, kwargs)),
                task_skipped=lambda key, **kwargs: task_events.append(("skipped", key, kwargs)),
                set_partial=lambda key, value: partials.__setitem__(key, value),
                save_category_rows=lambda rows: saved_groups.append(rows),
                download_url=lambda _path: "",
                build_task_meta=lambda svn_result, status, extra: {
                    "status": status,
                    "sourceType": svn_result["source_type"],
                    "workspaceRoot": svn_result["workspace_root"],
                    **extra,
                },
                build_svn_section=lambda _svn_result: {"branchChanged": [], "trunkConflict": []},
                build_changes=lambda _svn_result: [],
                build_conflicts=lambda _svn_result: [],
                build_lineage_summary=lambda *_args, **_kwargs: {"resultTables": [], "jobs": [], "warnings": []},
                build_config_files=lambda _paths: [],
                build_job_table=lambda *_args, **_kwargs: None,
                build_ai=lambda *_args, **_kwargs: None,
                get_active_profile_name=lambda: "local_pg",
                collect_hcyt_input_files=lambda **_kwargs: _InputFiles(),
                build_source_classified_progress=lambda **kwargs: {"changes": kwargs["changes"], "conflicts": kwargs["conflicts"]},
                publish_hcyt_progress=lambda set_partial, payload: set_partial("changes", payload["changes"]) or set_partial("conflicts", payload["conflicts"]),
                run_hcyt_rules=lambda *_args, **_kwargs: ([], [], []),
                run_hcyt_inspections=lambda **_kwargs: types.SimpleNamespace(
                    schedule={"rows": []},
                    py_scripts=[],
                    ref_tables=[],
                    deps=[],
                    asset_issues=[],
                    unified_asset_issues=[],
                    lineage_summary={"resultTables": [], "jobs": [], "warnings": [], "recvPlans": [], "sysNames": [], "outfiles": [], "stats": {}},
                ),
                run_hcyt_ai_review=lambda **_kwargs: None,
                sync_hcyt_legacy_results=lambda save_category_rows, grouped: save_category_rows(grouped),
                build_hcyt_report=lambda **kwargs: {
                    "task": kwargs["task"],
                    "svn": kwargs["svn"],
                    "changes": kwargs["changes"],
                    "conflicts": kwargs["conflicts"],
                    "dws": kwargs["grouped"]["dws"],
                    "hive": kwargs["grouped"]["hive"],
                    "python": kwargs["grouped"]["python"],
                    "sbin": kwargs["grouped"]["sbin"],
                    "config": kwargs["grouped"]["config"],
                    "recv": kwargs["grouped"]["recv"],
                    "sqlChecks": kwargs["sql_checks"],
                    "configFiles": kwargs["config_files"],
                    "schedule": kwargs["schedule"],
                    "pyScripts": kwargs["py_scripts"],
                    "refTables": kwargs["ref_tables"],
                    "deps": kwargs["deps"],
                    "assetIssues": kwargs["asset_issues"],
                    "unifiedAssetIssues": kwargs["unified_asset_issues"],
                    "lineageSummary": kwargs["lineage_summary"],
                },
                run_hcyt_schedule=lambda *_args, **_kwargs: None,
                run_hcyt_programs=lambda *_args, **_kwargs: None,
                text_to_rows=lambda *_args, **_kwargs: [],
                status_of=lambda errors, warnings: "fail" if errors else ("warn" if warnings else "pass"),
                count_levels=lambda _rows: (0, 0),
            ),
            partials,
            task_events,
            saved_groups,
        )

    def test_report_contract_and_task_event_order_remain_stable(self):
        context, partials, task_events, saved_groups = self._context()

        report = run_hcyt(context)

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "changes",
                "conflicts",
                "dws",
                "hive",
                "python",
                "sbin",
                "config",
                "recv",
                "sqlChecks",
                "configFiles",
                "schedule",
                "pyScripts",
                "refTables",
                "deps",
                "assetIssues",
                "unifiedAssetIssues",
                "lineageSummary",
            ],
        )
        self.assertEqual(partials["changes"], [])
        self.assertEqual(partials["conflicts"], [])
        self.assertEqual(task_events[0], ("running", "classify_files"))
        self.assertEqual(task_events[1][0:2], ("success", "classify_files"))
        self.assertEqual(task_events[2][0:2], ("success", "trunk_conflicts"))
        self.assertEqual(saved_groups, [])


if __name__ == "__main__":
    unittest.main()
