import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from audit.nups_runner import run_nups  # noqa: E402
from audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


class NupsRunnerTests(unittest.TestCase):
    def _build_context(self):
        saved_groups = []
        updates = []

        mods = types.SimpleNamespace(
            nups_rule=types.SimpleNamespace(
                get_nups_type=lambda _paths: (["/tmp/query.sql"], ["/tmp/job.py"]),
                rule_dws=lambda _path: ("bad sql", 1),
                rule_dws_py=lambda _path: ("warn py", 1, ["dm.table_a", "dm.table_a"]),
                get_program_table_name=lambda _path: "DM.TABLE_A",
            ),
            re_service=types.SimpleNamespace(
                get_filename=lambda path: Path(path).name,
                safe_remove_prefix=lambda path: f"rel/{Path(path).name}",
            ),
        )

        context = WorkflowRuntimeContext(
            mods=mods,
            workflow="nups",
            repo="svn://repo/nups/demo",
            task_id=2,
            ai_enabled=True,
            source_payload={
                "exported_paths": ["query.sql", "job.py"],
                "branch_changed_files": ["query.sql", "job.py"],
                "trunk_conflict_files": ["conflict.sql"],
                "create_revision": "2",
                "source_type": "svn",
                "workspace_root": "",
            },
            safe=lambda _label, fn, _default: fn(),
            log=lambda *_args, **_kwargs: None,
            update=lambda **kwargs: updates.append(kwargs),
            task_running=lambda *_args, **_kwargs: None,
            task_success=lambda *_args, **_kwargs: None,
            task_skipped=lambda *_args, **_kwargs: None,
            set_partial=lambda *_args, **_kwargs: None,
            save_category_rows=lambda rows: saved_groups.append(rows),
            download_url=lambda path: f"download://{Path(path).name}",
            build_task_meta=lambda _svn_result, status, extra: {"status": status, **extra},
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
            get_active_profile_name=lambda: "unused",
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
        return context, saved_groups, updates

    def test_run_nups_preserves_sql_python_and_legacy_shapes(self):
        context, saved_groups, updates = self._build_context()

        report = run_nups(context)

        self.assertEqual([update["progress"] for update in updates], [45, 65])
        self.assertEqual(report["sqlChecks"][0]["script"], "query.sql")
        self.assertEqual(report["sqlChecks"][0]["messages"][0]["level"], "err")
        self.assertEqual(report["pyScripts"][0]["script"], "job.py")
        self.assertEqual(report["pyScripts"][0]["path"], "rel/job.py")
        self.assertEqual(report["pyScripts"][0]["table"], "DM.TABLE_A")
        self.assertEqual(report["pyScripts"][0]["sqlRefs"], ["DM.TABLE_A"])
        self.assertEqual(report["conflicts"], ["conflict.sql"])
        self.assertEqual(saved_groups, [])
        self.assertEqual(report["ai"]["targets"], ["/tmp/job.py"])


if __name__ == "__main__":
    unittest.main()
