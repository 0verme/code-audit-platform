from __future__ import annotations

import time

from ...core.runtime import WorkflowRuntimeContext
from ...shared.report_helpers import build_source_file


def build_sql_analysis_message(*, dws_url, hive_url):
    sql_types = []
    if hive_url:
        sql_types.append("hive")
    if dws_url:
        sql_types.append("dws")
    if not sql_types:
        return None
    return f"分析 SQL 执行语句 {'/'.join(sql_types)}"


def build_hcyt_timing_milestone(
    label,
    phase,
    *,
    has_schedule=False,
    has_programs=False,
    **fields,
):
    if phase == "start":
        if label == "inspections.programs" and has_programs:
            return "分析加工脚本代码规范"
        return None

    if phase != "end":
        return None

    try:
        elapsed = f"{float(fields['elapsed_ms']) / 1000:.2f}s"
    except (KeyError, TypeError, ValueError):
        return None

    if label == "schedule.job.load_db_jobs" and "rows" in fields:
        return f"JOB 线上作业查询完成：{fields['rows']} 行，{elapsed}"
    if label == "schedule.job.rules":
        return f"JOB 调度分析完成：{elapsed}"
    if label == "inspections.schedule" and has_schedule:
        return f"分析调度规范完成：{elapsed}"
    if label == "programs.file.rules" and has_programs and fields.get("file"):
        return f"加工程序规则检查完成：{fields['file']}，{elapsed}"
    if label == "inspections.programs" and has_programs:
        return f"加工程序检查完成：{elapsed}"
    return None


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
    dlo_meta_lists = getattr(input_files, "dlo_meta_lists", []) or []
    dlo_lists = getattr(input_files, "dlo_lists", []) or []
    has_schedule = any((plan_xls, seq_xls, cale_xls, job_xls))
    has_programs = bool(py_lists)

    def source_file(path, section, kind):
        if not path:
            return None
        if callable(context.build_source_file):
            return context.build_source_file(path, section=section, kind=kind)
        return build_source_file(
            path,
            section=section,
            kind=kind,
            download_url=context.download_url,
            relative_path=mods.re_service.safe_remove_prefix,
        )

    source_specs = [
        (dws_url, "dws", "dws"),
        (hive_url, "hive", "hive"),
        *((path, "python", "python") for path in py_lists),
        *((path, "python", "dwo") for path in dwo_lists),
        *((path, "python", "dwf") for path in dwf_lists),
        *((path, "sbin", "sbin") for path in sbin_lists),
        *((path, "config", "schema-config") for path in schame_config_lists),
        *((path, "recv", "recv-config") for path in recv_lists),
        *((path, "other-files", "dlo-meta") for path in dlo_meta_lists),
        *((path, "other-files", "dlo") for path in dlo_lists),
        (plan_xls, "schedule", "plan"),
        (seq_xls, "schedule", "seq"),
        (job_xls, "schedule", "job"),
        (cale_xls, "schedule", "cale"),
        (program_xls, "other-files", "program"),
    ]
    source_files = [
        descriptor
        for path, section, kind in source_specs
        if (descriptor := source_file(path, section, kind))
    ]

    def log_timing(label, phase, **fields):
        suffix = " ".join(f"{key}={value}" for key, value in fields.items())
        context.log(f"[timing] {label} {phase}" + (f" {suffix}" if suffix else ""), "INFO")
        milestone = build_hcyt_timing_milestone(
            label,
            phase,
            has_schedule=has_schedule,
            has_programs=has_programs,
            **fields,
        )
        if milestone:
            context.log(milestone, "INFO")

    context.publish_hcyt_progress(
        context.set_partial,
        context.build_source_classified_progress(changes=changes, conflicts=conflicts),
    )
    context.set_partial("sourceFiles", source_files)
    context.task_success("classify_files", summary={"changedFiles": len(changes)})
    context.task_success("trunk_conflicts", result=conflicts, summary={"conflicts": len(conflicts)})

    context.update(progress=35, step="SQL 与配置规则检查")
    sql_analysis_message = build_sql_analysis_message(dws_url=dws_url, hive_url=hive_url)
    if sql_analysis_message:
        context.log(sql_analysis_message, "INFO")
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
            },
        )(),
        grouped=grouped,
        task_running=context.task_running,
        task_success=context.task_success,
        task_skipped=context.task_skipped,
        set_partial=context.set_partial,
        download_url=context.download_url,
        build_config_files=context.build_config_files,
        log_timing=log_timing,
    ))

    context.update(progress=50, step="调度规范检查")
    if has_schedule:
        context.log("打印待上线调度信息", "INFO")
        context.log("分析调度规范", "INFO")
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
        log_timing=log_timing,
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
        source_files=source_files,
        metadata_profile=context.get_active_profile_name(),
        ai=ai,
    ))
