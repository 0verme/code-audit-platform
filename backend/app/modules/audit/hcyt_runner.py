from __future__ import annotations

import time

from .workflow_runtime import WorkflowRuntimeContext


def run_hcyt(context: WorkflowRuntimeContext) -> dict:
    mods = context.mods
    svn_result = context.source_payload

    def timed(label, fn):
        started = time.perf_counter()
        context.log(f"[timing] {label} start", "INFO")
        try:
            return fn()
        finally:
            context.log(
                f"[timing] {label} end elapsed_ms={round((time.perf_counter() - started) * 1000, 1)}",
                "INFO",
            )

    context.task_running("classify_files")
    input_files = timed("hcyt.classify_files", lambda: context.collect_hcyt_input_files(
        svn_result=svn_result,
        re_service=mods.re_service,
        hcyt=mods.hcyt,
        build_changes=context.build_changes,
        build_conflicts=context.build_conflicts,
    ))
    (
        dws_url,
        hive_url,
        schame_config_lists,
        sbin_lists,
        recv_lists,
        dwo_lists,
        dwf_lists,
        py_lists,
        plan_xls,
        seq_xls,
        job_xls,
        program_xls,
        cale_xls,
        grouped,
        changes,
        conflicts,
    ) = input_files.as_run_inputs()
    context.publish_hcyt_progress(
        context.set_partial,
        context.build_source_classified_progress(changes=changes, conflicts=conflicts),
    )
    context.task_success("classify_files", summary={"changedFiles": len(changes)})
    context.task_success("trunk_conflicts", result=conflicts, summary={"conflicts": len(conflicts)})

    context.update(progress=35, step="SQL 与配置规则检查")
    sql_checks, asset_issues, config_files = timed("hcyt.rules", lambda: context.run_hcyt_rules(
        dws_url,
        hive_url,
        schame_config_lists,
        sbin_lists,
        recv_lists,
        dwo_lists,
        dwf_lists,
        safe=context.safe,
        modules=type(
            "HcytRuleRunnerModules",
            (),
            {
                "re_service": mods.re_service,
                "hcyt": mods.hcyt,
                "hcyt_ddl_rule": getattr(
                    mods,
                    "hcyt_ddl_rule",
                    type(
                        "NoopDdlRule",
                        (),
                        {"collect_root_missing_issues": staticmethod(lambda *args, **kwargs: [])},
                    )(),
                ),
                "hcyt_sql_rule": getattr(
                    mods,
                    "hcyt_sql_rule",
                    type(
                        "NoopSqlRule",
                        (),
                        {"collect_created_table_review_issues": staticmethod(lambda *args, **kwargs: [])},
                    )(),
                ),
                "text_to_rows": staticmethod(context.text_to_rows),
            },
        )(),
        grouped=grouped,
        task_running=context.task_running,
        task_success=context.task_success,
        task_skipped=context.task_skipped,
        set_partial=context.set_partial,
        download_url=context.download_url,
        build_config_files=context.build_config_files,
        log_timing=lambda label, phase, **fields: context.log(
            f"[timing] {label} {phase} " + " ".join(f"{key}={value}" for key, value in fields.items()),
            "INFO",
        ),
    ))

    context.update(progress=50, step="调度规范检查")
    context.task_running("schedule")
    inspections = timed("hcyt.inspections", lambda: context.run_hcyt_inspections(
        plan_xls=plan_xls,
        seq_xls=seq_xls,
        cale_xls=cale_xls,
        job_xls=job_xls,
        py_lists=py_lists,
        program_xls=program_xls,
        task_id=context.task_id,
        initial_asset_issues=asset_issues,
        run_schedule=context.run_hcyt_schedule,
        run_programs=context.run_hcyt_programs,
        build_lineage_summary=context.build_lineage_summary,
        modules=mods,
        log_schedule_warning=lambda msg: context.log(msg, "WARN"),
        update_progress=context.update,
        task_running=context.task_running,
        task_success=context.task_success,
        set_partial=context.set_partial,
        grouped=grouped,
        log_timing=lambda label, phase, **fields: context.log(
            f"[timing] {label} {phase} " + " ".join(f"{key}={value}" for key, value in fields.items()),
            "INFO",
        ),
    ))
    schedule = inspections.schedule
    py_scripts = inspections.py_scripts
    ref_tables = inspections.ref_tables
    deps = inspections.deps
    asset_issues = inspections.asset_issues
    unified_asset_issues = inspections.unified_asset_issues
    lineage_summary = inspections.lineage_summary

    errors, warnings = context.count_levels(list(grouped.values()) + [schedule["rows"]])
    ai = timed("hcyt.ai_review", lambda: context.run_hcyt_ai_review(
        py_lists=py_lists,
        dws_url=dws_url,
        errors=errors,
        warnings=warnings,
        ai_enabled=context.ai_enabled,
        update_progress=context.update,
        build_ai=context.build_ai,
    ))

    status = context.status_of(errors + len(conflicts), warnings)
    checks = sum(
        1
        for flag in (
            dws_url,
            hive_url,
            sbin_lists,
            schame_config_lists,
            recv_lists,
            dwo_lists or dwf_lists,
            plan_xls,
            seq_xls,
            job_xls,
            py_lists,
        )
        if flag
    )

    return timed("hcyt.report", lambda: context.build_hcyt_report(
        task=context.build_task_meta(
            svn_result,
            status,
            {
                "changedFiles": len(changes),
                "checks": checks,
                "errors": errors,
                "warnings": warnings,
                "conflicts": len(conflicts),
                "sqlFiles": len(svn_result["exported_paths"]),
            },
        ),
        svn=context.build_svn_section(svn_result),
        changes=changes,
        conflicts=conflicts,
        grouped=grouped,
        sql_checks=sql_checks,
        config_files=config_files,
        schedule=schedule,
        py_scripts=py_scripts,
        ref_tables=ref_tables,
        deps=deps,
        asset_issues=asset_issues,
        unified_asset_issues=unified_asset_issues,
        lineage_summary=lineage_summary,
        ai=ai,
    ))
