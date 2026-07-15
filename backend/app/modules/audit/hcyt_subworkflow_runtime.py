from __future__ import annotations

from types import SimpleNamespace

from .hcyt_program_runner import run_hcyt_programs as _run_hcyt_programs
from .hcyt_schedule_runner import run_hcyt_schedule as _run_hcyt_schedule, schedule_rows as _schedule_rows


def run_hcyt_schedule(
    plan_xls,
    seq_xls,
    cale_xls,
    job_xls,
    *,
    safe,
    modules,
    build_job_table,
    rule_label,
    log_timing=None,
):
    return _run_hcyt_schedule(
        plan_xls,
        seq_xls,
        cale_xls,
        job_xls,
        safe=safe,
        modules=modules,
        build_job_table=build_job_table,
        schedule_rows_fn=lambda result_text, warn_text: _schedule_rows(
            result_text,
            warn_text,
            rule_label=rule_label,
        ),
        log_timing=log_timing,
    )


def run_hcyt_programs(
    py_lists,
    job_df,
    program_xls,
    db_job_rows,
    *,
    safe,
    modules,
    download_url,
    load_result_table_annotations,
    annotate_table,
    profile_name,
    normalize_table,
    dedupe_tables,
    cale_map,
    text_to_rows,
    log_timing=None,
    lineage_context=None,
):
    return _run_hcyt_programs(
        py_lists,
        job_df,
        program_xls,
        db_job_rows,
        safe=safe,
        modules=_build_hcyt_program_modules(modules, text_to_rows=text_to_rows),
        download_url=download_url,
        load_result_table_annotations=load_result_table_annotations,
        annotate_table=annotate_table,
        profile_name=profile_name,
        normalize_table=normalize_table,
        dedupe_tables=dedupe_tables,
        cale_map=cale_map,
        log_timing=log_timing,
        lineage_context=lineage_context,
    )


def _build_hcyt_program_modules(modules, *, text_to_rows):
    return SimpleNamespace(
        re_service=modules.re_service,
        hcyt=modules.hcyt,
        public_data=getattr(modules, "public_data", _noop_public_data()),
        hcyt_python_rule=getattr(modules, "hcyt_python_rule", _noop_python_rule()),
        hcyt_ddl_rule=getattr(modules, "hcyt_ddl_rule", _noop_ddl_rule()),
        load_registered_result_tables=getattr(
            modules,
            "load_registered_result_tables",
            lambda *, profile: set(),
        ),
        text_to_rows=text_to_rows,
    )


def _noop_public_data():
    return SimpleNamespace(
        all_para_table_lists=lambda: [],
        all_job=lambda: [],
    )


def _noop_python_rule():
    return SimpleNamespace(
        build_asset_table_review_issues=lambda *args, **kwargs: [],
    )


def _noop_ddl_rule():
    return SimpleNamespace(
        collect_root_missing_issues=lambda *args, **kwargs: [],
    )
