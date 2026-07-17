import sys
import types
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.audit.hcyt_runner import (  # noqa: E402
    build_hcyt_timing_milestone,
    build_sql_analysis_message,
    run_hcyt,
)
from app.modules.audit.workflow_runtime import WorkflowRuntimeContext  # noqa: E402


class _InputFiles:
    def __init__(self, *, with_milestones=False):
        self.with_milestones = with_milestones

    def as_run_inputs(self):
        grouped = {"dws": [], "hive": [], "python": [], "sbin": [], "config": [], "recv": []}
        return (
            "dws.sql" if self.with_milestones else None,
            "hive.sql" if self.with_milestones else None,
            [],
            [],
            [],
            [],
            [],
            ["first.py", "second.py"] if self.with_milestones else [],
            None,
            None,
            "job.xlsx" if self.with_milestones else None,
            None,
            None,
            grouped,
            [{"path": "demo.sql"}],
            [],
        )


class HcytRunnerTests(unittest.TestCase):
    def test_sql_analysis_message_uses_available_sql_types(self):
        self.assertEqual(
            build_sql_analysis_message(dws_url="dws.sql", hive_url="hive.sql"),
            "分析 SQL 执行语句 hive/dws",
        )
        self.assertEqual(
            build_sql_analysis_message(dws_url="dws.sql", hive_url=None),
            "分析 SQL 执行语句 dws",
        )
        self.assertEqual(
            build_sql_analysis_message(dws_url=None, hive_url="hive.sql"),
            "分析 SQL 执行语句 hive",
        )
        self.assertIsNone(build_sql_analysis_message(dws_url=None, hive_url=None))

    def test_timing_milestones_match_legacy_user_facing_details(self):
        self.assertEqual(
            build_hcyt_timing_milestone(
                "schedule.job.load_db_jobs", "end", elapsed_ms=4200, rows=31103
            ),
            "JOB 线上作业查询完成：31103 行，4.20s",
        )
        self.assertEqual(
            build_hcyt_timing_milestone("schedule.job.rules", "end", elapsed_ms=4660),
            "JOB 调度分析完成：4.66s",
        )
        self.assertEqual(
            build_hcyt_timing_milestone(
                "inspections.schedule", "end", has_schedule=True, elapsed_ms=4940
            ),
            "分析调度规范完成：4.94s",
        )
        self.assertEqual(
            build_hcyt_timing_milestone(
                "inspections.programs", "start", has_programs=True
            ),
            "分析加工脚本代码规范",
        )
        self.assertEqual(
            build_hcyt_timing_milestone(
                "programs.file.rules",
                "end",
                has_programs=True,
                file="005_DWS_DWM_M_SXED_1_01.py",
                elapsed_ms=1890,
            ),
            "加工程序规则检查完成：005_DWS_DWM_M_SXED_1_01.py，1.89s",
        )
        self.assertEqual(
            build_hcyt_timing_milestone(
                "inspections.programs", "end", has_programs=True, elapsed_ms=3550
            ),
            "加工程序检查完成：3.55s",
        )

    def test_timing_milestones_skip_missing_inputs_and_incomplete_fields(self):
        self.assertIsNone(build_hcyt_timing_milestone(
            "inspections.schedule", "end", elapsed_ms=100
        ))
        self.assertIsNone(build_hcyt_timing_milestone(
            "inspections.programs", "start", has_programs=False
        ))
        self.assertIsNone(build_hcyt_timing_milestone(
            "programs.file.rules", "end", has_programs=True, elapsed_ms=100
        ))
        self.assertIsNone(build_hcyt_timing_milestone(
            "schedule.job.load_db_jobs", "end", elapsed_ms=100
        ))
        self.assertIsNone(build_hcyt_timing_milestone(
            "schedule.job.rules", "end"
        ))

    def test_run_hcyt_preserves_orchestration_order(self):
        calls = []
        saved_groups = []

        def run_inspections(**kwargs):
            log_timing = kwargs["log_timing"]
            log_timing("schedule.job.load_db_jobs", "end", rows=31103, elapsed_ms=4200)
            log_timing("schedule.job.rules", "end", elapsed_ms=4660)
            log_timing("inspections.schedule", "end", elapsed_ms=4940)
            log_timing("inspections.programs", "start")
            log_timing("programs.file.rules", "end", file="first.py", elapsed_ms=1230)
            log_timing("programs.file.rules", "end", file="second.py", elapsed_ms=2340)
            log_timing("inspections.programs", "end", elapsed_ms=3550)
            return types.SimpleNamespace(
                schedule={"rows": []},
                py_scripts=[],
                ref_tables=[],
                deps=[],
                asset_issues=[],
                unified_asset_issues=[],
                lineage_summary={"resultTables": [], "jobs": [], "warnings": []},
            )

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
            collect_hcyt_input_files=lambda **_kwargs: _InputFiles(with_milestones=True),
            build_source_classified_progress=lambda **kwargs: {"changes": kwargs["changes"], "conflicts": kwargs["conflicts"]},
            publish_hcyt_progress=lambda set_partial, payload: calls.append(("publish", payload)),
            run_hcyt_rules=lambda *_args, **_kwargs: ([], [], []),
            run_hcyt_inspections=run_inspections,
            run_hcyt_ai_review=lambda **_kwargs: None,
            sync_hcyt_legacy_results=lambda save_category_rows, grouped: (
                calls.append(("legacy", list(grouped.keys()))),
                save_category_rows(grouped),
            )[-1],
            build_hcyt_report=lambda **kwargs: calls.append(("report", kwargs["changes"], kwargs["metadata_profile"])) or {"task": {"status": "pass"}},
            run_hcyt_schedule=lambda *_args, **_kwargs: None,
            run_hcyt_programs=lambda *_args, **_kwargs: None,
            status_of=lambda errors, warnings: "fail" if errors else ("warn" if warnings else "pass"),
            count_levels=lambda _rows: (0, 0),
        )

        report = run_hcyt(context)

        self.assertEqual(report, {"task": {"status": "pass"}})
        self.assertIn(("task_running", "classify_files"), calls)
        self.assertIn(("publish", {"changes": [{"path": "demo.sql"}], "conflicts": []}), calls)
        self.assertIn(("report", [{"path": "demo.sql"}], "local_pg"), calls)
        self.assertEqual(saved_groups, [])
        user_logs = [
            event[2]
            for event in calls
            if event[0] == "log" and not event[2].startswith("[timing]")
        ]
        self.assertEqual(user_logs, [
            "分析 SQL 执行语句 hive/dws",
            "打印待上线调度信息",
            "分析调度规范",
            "JOB 线上作业查询完成：31103 行，4.20s",
            "JOB 调度分析完成：4.66s",
            "分析调度规范完成：4.94s",
            "分析加工脚本代码规范",
            "加工程序规则检查完成：first.py，1.23s",
            "加工程序规则检查完成：second.py，2.34s",
            "加工程序检查完成：3.55s",
        ])


if __name__ == "__main__":
    unittest.main()
