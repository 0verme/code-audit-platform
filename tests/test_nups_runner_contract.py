import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.nups_runner import run_nups  # noqa: E402
from app.modules.audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


class NupsRunnerContractTests(unittest.TestCase):
    def _context(self, *, build_ai=None, sql_rule=None, py_rule=None):
        saved_groups = []
        logs = []

        def safe(label, fn, default):
            try:
                return fn()
            except Exception as exc:
                logs.append(f"{label}:{exc}")
                return default

        mods = types.SimpleNamespace(
            nups_rule=types.SimpleNamespace(
                get_nups_type=lambda _paths: (["/tmp/query.sql"], ["/tmp/job.py"]),
                rule_dws=sql_rule or (lambda _path: ("", 0)),
                rule_dws_py=py_rule or (lambda _path: ("", 0, [])),
                get_program_table_name=lambda _path: "DM.TABLE_A",
            ),
            re_service=types.SimpleNamespace(
                get_filename=lambda path: Path(path).name,
                safe_remove_prefix=lambda path: path,
            ),
        )

        context = WorkflowRuntimeContext(
            mods=mods,
            workflow="nups",
            repo="svn://repo/nups/demo",
            task_id=3,
            ai_enabled=True,
            source_payload={
                "exported_paths": ["query.sql", "job.py"],
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
            build_ai=build_ai or (lambda _targets, _errors, _warnings: None),
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
        return context, saved_groups, logs

    def test_report_contract_keeps_source_payload_outside_top_level(self):
        context, saved_groups, _logs = self._context()

        report = run_nups(context)

        self.assertEqual(
            list(report.keys()),
            [
                "task",
                "svn",
                "changes",
                "conflicts",
                "sqlChecks",
                "pyScripts",
                "assetIssues",
                "unifiedAssetIssues",
            ],
        )
        self.assertEqual(report["task"]["sourceType"], "svn")
        self.assertNotIn("source", report)
        self.assertNotIn("sourceType", report)
        self.assertNotIn("workspaceRoot", report)
        self.assertEqual(saved_groups, [])

    def test_ai_passthrough_supports_enabled_disabled_and_degraded_cases(self):
        context, _saved_groups, _logs = self._context(
            build_ai=lambda targets, errors, warnings: {
                "targets": list(targets),
                "errors": errors,
                "warnings": warnings,
            }
        )
        report = run_nups(context)
        self.assertEqual(report["ai"]["targets"], ["/tmp/job.py"])

        context, _saved_groups, _logs = self._context(build_ai=lambda _targets, _errors, _warnings: None)
        report = run_nups(context)
        self.assertNotIn("ai", report)

        context, _saved_groups, _logs = self._context(
            build_ai=lambda _targets, _errors, _warnings: {"summary": "degraded", "level": "warn"}
        )
        report = run_nups(context)
        self.assertEqual(report["ai"]["summary"], "degraded")

    def test_rule_failures_still_degrade_through_safe_defaults(self):
        context, _saved_groups, logs = self._context(
            sql_rule=lambda _path: (_ for _ in ()).throw(RuntimeError("sql boom")),
            py_rule=lambda _path: (_ for _ in ()).throw(RuntimeError("py boom")),
        )

        report = run_nups(context)

        self.assertEqual(report["task"]["status"], "pass")
        self.assertEqual(report["sqlChecks"][0]["messages"], [])
        self.assertEqual(report["pyScripts"][0]["messages"], [])
        self.assertTrue(any("NUPS SQL 规则:sql boom" in log for log in logs))
        self.assertTrue(any("NUPS 加工程序规则(job.py):py boom" in log for log in logs))


if __name__ == "__main__":
    unittest.main()
