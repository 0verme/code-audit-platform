import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
SVN_CHECK_DIR = BACKEND_DIR / "svn_check"
for path in (BACKEND_DIR, SVN_CHECK_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from audit.hcyt_runner import run_hcyt  # noqa: E402
from audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


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
            [{"path": "demo.sql"}],
            [],
        )


class HcytRunnerTests(unittest.TestCase):
    def test_run_hcyt_preserves_orchestration_order(self):
        calls = []
        saved_groups = []

        context = WorkflowRuntimeContext(
            mods=types.SimpleNamespace(re_service=types.SimpleNamespace(), hcyt=types.SimpleNamespace()),
            workflow="hcyt",
            repo="svn://repo/hcyt/demo",
            task_id=7,
            ai_enabled=False,
            source_payload={
                "exported_paths": ["demo.sql"],
                "branch_changed_files": ["demo.sql"],
                "trunk_conflict_files": [],
                "create_revision": "123",
                "source_type": "svn",
                "workspace_root": "",
            },
            safe=lambda _label, fn, _default: fn(),
            log=lambda msg, level="INFO": calls.append(("log", level, msg)),
            update=lambda **kwargs: calls.append(("update", kwargs["progress"])),
            task_running=lambda key: calls.append(("task_running", key)),
            task_success=lambda key, **kwargs: calls.append(("task_success", key, kwargs)),
            task_skipped=lambda key, **kwargs: calls.append(("task_skipped", key, kwargs)),
            set_partial=lambda key, value: calls.append(("partial", key, value)),
            save_category_rows=lambda rows: saved_groups.append(rows),
            download_url=lambda path: f"download://{Path(path).name}",
            build_task_meta=lambda _svn_result, status, extra: {"status": status, **extra},
            build_svn_section=lambda _svn_result: {"branchChanged": ["demo.sql"], "trunkConflict": []},
            build_changes=lambda _svn_result: [{"path": "demo.sql"}],
            build_conflicts=lambda _svn_result: [],
            build_lineage_summary=lambda *_args, **_kwargs: {"resultTables": [], "jobs": [], "warnings": []},
            build_config_files=lambda _paths: [],
            build_job_table=lambda *_args, **_kwargs: None,
            build_ai=lambda *_args, **_kwargs: None,
            get_active_profile_name=lambda: "local_pg",
            collect_hcyt_input_files=lambda **_kwargs: _InputFiles(),
            build_source_classified_progress=lambda **kwargs: {"changes": kwargs["changes"], "conflicts": kwargs["conflicts"]},
            publish_hcyt_progress=lambda set_partial, payload: calls.append(("publish", payload)),
            run_hcyt_rules=lambda *_args, **_kwargs: ([], [], []),
            run_hcyt_inspections=lambda **_kwargs: types.SimpleNamespace(
                schedule={"rows": []},
                py_scripts=[],
                ref_tables=[],
                deps=[],
                asset_issues=[],
                unified_asset_issues=[],
                lineage_summary={"resultTables": [], "jobs": [], "warnings": []},
            ),
            run_hcyt_ai_review=lambda **_kwargs: None,
            sync_hcyt_legacy_results=lambda save_category_rows, grouped: (
                calls.append(("legacy", list(grouped.keys()))),
                save_category_rows(grouped),
            )[-1],
            build_hcyt_report=lambda **kwargs: calls.append(("report", kwargs["changes"])) or {"task": {"status": "pass"}},
            run_hcyt_schedule=lambda *_args, **_kwargs: None,
            run_hcyt_programs=lambda *_args, **_kwargs: None,
            text_to_rows=lambda *_args, **_kwargs: [],
            status_of=lambda errors, warnings: "fail" if errors else ("warn" if warnings else "pass"),
            count_levels=lambda _rows: (0, 0),
        )

        report = run_hcyt(context)

        self.assertEqual(report, {"task": {"status": "pass"}})
        self.assertIn(("task_running", "classify_files"), calls)
        self.assertIn(("publish", {"changes": [{"path": "demo.sql"}], "conflicts": []}), calls)
        self.assertIn(("legacy", ["dws", "hive", "python", "sbin", "config", "recv"]), calls)
        self.assertIn(("report", [{"path": "demo.sql"}]), calls)
        self.assertEqual(saved_groups[0]["dws"], [])


if __name__ == "__main__":
    unittest.main()
