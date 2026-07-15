from __future__ import annotations

import time

from dataclasses import dataclass

from .issue_adapter import asset_issue_to_dict
from .hcyt_progress_events import (
    build_lineage_checked_progress,
    build_program_checked_progress,
    publish_hcyt_progress,
)


@dataclass
class HcytInspectionResult:
    schedule: dict
    schedule_warning: str | None
    py_scripts: list
    py_rows: list
    ref_tables: list
    deps: list
    asset_issues: list
    unified_asset_issues: list
    lineage_summary: dict


def build_schedule_shape_mismatch_result(exc):
    return {
        "summary": {"plan": 0, "seq": 0, "job": 0, "cycles": 0, "missing": 0},
        "rows": [{
            "table": "SCHEDULE",
            "item": "",
            "rule": "column-check",
            "level": "warn",
            "msg": f"schedule artifact shape mismatch: {exc}",
        }],
        "tables": {},
        "_job_df": None,
        "_r_plan": None,
        "_db_job_rows": None,
    }


def run_hcyt_inspections(
    *,
    plan_xls,
    seq_xls,
    cale_xls,
    job_xls,
    py_lists,
    program_xls,
    task_id,
    initial_asset_issues,
    run_schedule,
    run_programs,
    build_lineage_summary,
    modules,
    log_schedule_warning=None,
    update_progress=None,
    task_running=None,
    task_success=None,
    set_partial=None,
    grouped=None,
    log_timing=None,
):
    schedule_warning = None
    try:
        started = time.perf_counter()
        if log_timing is not None:
            log_timing("inspections.schedule", "start")
        try:
            schedule = run_schedule(plan_xls, seq_xls, cale_xls, job_xls)
        finally:
            if log_timing is not None:
                log_timing("inspections.schedule", "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1))
    except IndexError as exc:
        schedule_warning = f"调度 Excel 结构异常，已跳过调度规则检查: {exc}"
        schedule = build_schedule_shape_mismatch_result(exc)
    if schedule_warning and log_schedule_warning is not None:
        log_schedule_warning(schedule_warning)

    job_df = schedule.pop("_job_df")
    schedule.pop("_r_plan")
    db_job_rows = schedule.pop("_db_job_rows")
    if set_partial is not None:
        set_partial("schedule", schedule)
    if task_success is not None:
        task_success("schedule", result=schedule, summary={"issues": len(schedule.get("rows", []))})

    if update_progress is not None:
        update_progress(progress=65, step="加工程序检查")
    if task_running is not None:
        task_running("python_scripts")
    started = time.perf_counter()
    if log_timing is not None:
        log_timing("inspections.programs", "start")
    try:
        py_scripts, py_rows, ref_tables, deps, py_asset_issues = run_programs(
            py_lists, job_df, program_xls, db_job_rows
        )
    finally:
        if log_timing is not None:
            log_timing("inspections.programs", "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1))
    if grouped is not None:
        grouped["python"] += py_rows
    if set_partial is not None:
        publish_hcyt_progress(set_partial, build_program_checked_progress(
            python_rows=grouped["python"] if grouped is not None else py_rows,
            py_scripts=py_scripts,
            ref_tables=ref_tables,
            deps=deps,
        ))
    if task_success is not None:
        result_rows = grouped["python"] if grouped is not None else py_rows
        task_success("python_scripts", result=result_rows, summary={"issues": len(result_rows)})

    asset_issues = list(initial_asset_issues or [])
    asset_issues += py_asset_issues
    asset_issues = [asset_issue_to_dict(issue) for issue in modules.dedupe_issues(asset_issues)]
    unified_asset_issues = modules.asset_issues_to_unified_issues(
        asset_issues,
        scan_batch_id=task_id,
    )
    if task_running is not None:
        task_running("lineage")
    started = time.perf_counter()
    if log_timing is not None:
        log_timing("inspections.lineage", "start")
    try:
        lineage_summary = build_lineage_summary(
            modules,
            job_df=job_df,
            program_xls=program_xls,
            py_lists=py_lists,
            db_job_rows=db_job_rows,
        )
    finally:
        if log_timing is not None:
            log_timing("inspections.lineage", "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1))
    if set_partial is not None:
        publish_hcyt_progress(set_partial, build_lineage_checked_progress(
            asset_issues=asset_issues,
            unified_asset_issues=unified_asset_issues,
            lineage_summary=lineage_summary,
        ))
    if task_success is not None:
        task_success("lineage", result=lineage_summary, summary=lineage_summary.get("stats", {}))
    return HcytInspectionResult(
        schedule=schedule,
        schedule_warning=schedule_warning,
        py_scripts=py_scripts,
        py_rows=py_rows,
        ref_tables=ref_tables,
        deps=deps,
        asset_issues=asset_issues,
        unified_asset_issues=unified_asset_issues,
        lineage_summary=lineage_summary,
    )
