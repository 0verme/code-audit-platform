from __future__ import annotations

import time


def _timed(label, fn, log_timing=None, **fields):
    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, "start", **fields)
    try:
        return fn()
    finally:
        if log_timing is not None:
            log_timing(label, "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **fields)


def _load_lineage_metadata(modules, log_timing):
    """Load lineage metadata once and retain the raw rows for this audit run."""
    metadata_service = getattr(modules, "audit_metadata_service", None)
    context = {
        "job_outfile_rows": [], "result_table_recv_detail_rows": [],
        "result_table_sys_name_rows": [], "recv_mapping_plan_rows": [], "warnings": [],
    }
    if metadata_service is None:
        context["warnings"].append("lineage metadata unavailable")
        return context
    queries = (
        ("job_outfile_rows", "programs.metadata.job_outfiles", "job outfile metadata", metadata_service.list_job_outfiles),
        ("result_table_recv_detail_rows", "programs.metadata.recv_details", "result table recv detail metadata", metadata_service.list_result_table_recv_details),
        ("result_table_sys_name_rows", "programs.metadata.sys_names", "result table sys name metadata", metadata_service.list_result_table_sys_names),
        ("recv_mapping_plan_rows", "programs.metadata.mapping_plans", "recv mapping plan metadata", metadata_service.list_recv_mapping_plans),
    )
    for key, label, description, query in queries:
        try:
            context[key] = _timed(label, lambda query=query: query() or [], log_timing)
        except Exception as exc:
            context["warnings"].append(f"{description} unavailable: {type(exc).__name__}")
    return context


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
    log_timing=None,
    lineage_context=None,
):
    py_scripts, py_rows, ref_tables, deps, asset_issues = [], [], [], [], []
    if not py_lists:
        return py_scripts, py_rows, ref_tables, deps, asset_issues

    program_lookup = dependency_lookup = None
    merge_df = None
    lineage_rows_by_path = {}
    if job_df is not None and program_xls:
        def build_lookups():
            program_df = _timed("programs.load_excel", lambda: modules.re_service.load_xls_to_df(program_xls), log_timing)
            merge_job = modules.hcyt.all_job_df(job_df, db_job_rows) if db_job_rows is not None else job_df
            try:
                merge_program = _timed("programs.normalize_excel", lambda: modules.hcyt.all_program_df(program_df), log_timing)
            except Exception:
                merge_program = program_df
            prog_path_col = merge_program.columns[4]
            merged = _timed("programs.merge_job_program", lambda: modules.re_service.merge_job_program(merge_job, merge_program), log_timing)
            return (
                merged,
                _timed("programs.build_program_lookup", lambda: modules.re_service.build_program_lookup(merged, prog_path_col, tail_levels=4), log_timing),
                _timed("programs.build_dependency_lookup", lambda: modules.re_service.build_dependency_table_lookup(merged), log_timing),
                _timed("programs.build_lineage_row_lookup", lambda: modules.re_service.build_lineage_row_lookup(merged, tail_levels=4), log_timing, merge_rows=len(merged.index)),
            )

        merge_df, program_lookup, dependency_lookup, lineage_rows_by_path = _timed(
            "programs.build_lookups",
            lambda: safe("JOB/PROGRAM 调度关联", build_lookups, (None, None, None, {})),
            log_timing,
        )

    if lineage_context is not None:
        lineage_context.update(_load_lineage_metadata(modules, log_timing))
        lineage_context.update({
            "merge_df": merge_df,
            "program_lookup": program_lookup,
            "dependency_lookup": dependency_lookup,
            "lineage_rows_by_path": lineage_rows_by_path,
            "job_outfile_lookup": modules.re_service.build_job_outfile_lookup(
                lineage_context.get("job_outfile_rows")
            ),
        })

    registered = set(_timed(
        "programs.load_registered_tables",
        lambda: safe(
            "结果表登记库(lineage)",
            lambda: modules.load_registered_result_tables(profile=profile_name),
            set(),
        ),
        log_timing,
    ))
    para_tables = set(_timed(
        "programs.load_parameter_tables",
        lambda: safe(
            "码值参数表(all_para_table_lists)",
            lambda: {normalize_table(row[0]) for row in modules.public_data.all_para_table_lists() if row and row[0]},
            set(),
        ),
        log_timing,
    ))
    disabled, sys_name_map = _timed("programs.load_annotations", load_result_table_annotations, log_timing)
    disabled_job_names = set(_timed(
        "programs.load_disabled_jobs",
        lambda: safe(
            "禁用作业(all_job)",
            lambda: {
                str(row[2]).strip().upper()
                for row in (db_job_rows or modules.public_data.all_job() or [])
                if len(row) > 23 and row[2] and str(row[23]).strip() in ("9", "9.0")
            },
            set(),
        ),
        log_timing,
    ))

    upstream_tables, job_names = [], []
    for path in py_lists:
        file_name = modules.re_service.get_filename(path)
        file_fields = {"file": file_name}
        result = _timed("programs.file.rules", lambda: safe(f"加工程序规则({file_name})", lambda p=path: modules.hcyt.rule_dws_py(p), ("", "", 0, [])), log_timing, **file_fields)
        lint = modules.text_to_rows(result[0], result[1], file_name)
        sql_tables = dedupe_tables(result[3] if len(result) > 3 else [])
        table_name = _timed("programs.file.table_name", lambda: safe("表名解析", lambda p=path: modules.hcyt.get_program_table_name(p), ""), log_timing, **file_fields)
        source_text = _timed("programs.file.read_source", lambda: safe(f"加工程序内容读取({file_name})", lambda p=path: modules.re_service.read_data_from_file(p), ""), log_timing, **file_fields)
        job_name, freq, yilai_tables = "", "", None
        if program_lookup is not None:
            def lookup(p=path):
                info = modules.re_service.get_program_lookup_result(
                    program_lookup, modules.re_service.safe_remove_prefix(p), tail_levels=4
                )
                yilai = modules.re_service.get_yilai_table_from_lookup(info[2], dependency_lookup)
                return info[0], info[1], yilai

            looked = _timed("programs.file.schedule_lookup", lambda: safe(f"调度信息关联({file_name})", lookup, ("", "", None)), log_timing, **file_fields)
            job_name = str(looked[0] or "")
            freq = cale_map.get(looked[1], str(looked[1] or ""))
            yilai_tables = dedupe_tables(looked[2]) if looked[2] is not None else None

        if table_name:
            asset_issues += safe(
                f"加工程序资产表待核对 issue({file_name})",
                lambda output_table=table_name, source=file_name: modules.hcyt_python_rule.build_asset_table_review_issues(
                    [output_table], "hcyt", source
                ),
                [],
            )
        asset_issues += safe(
            f"加工程序词根结构化 issue({file_name})",
            lambda text=source_text, source=file_name: modules.hcyt_ddl_rule.collect_root_missing_issues(
                text, "hcyt", source
            ),
            [],
        )

        current_result_tables = registered | ({normalize_table(table_name)} if table_name else set())
        result_tables = [name for name in sql_tables if name in current_result_tables]
        code_tables = [name for name in sql_tables if name in para_tables]
        middle_tables = [name for name in sql_tables if name not in current_result_tables and name not in para_tables]

        compare_rows = []
        if yilai_tables is not None:
            left, right = set(result_tables), set(yilai_tables)
            for name in sorted(left & right):
                ann = annotate_table(name, disabled, sys_name_map)
                compare_rows.append({"sql": name, "dep": name, "state": "same", **ann})
            for name in sorted(left - right):
                ann = annotate_table(name, disabled, sys_name_map)
                compare_rows.append({"sql": name, "dep": None, "state": "missing", **ann})
            for name in sorted(right - left):
                compare_rows.append(
                    {
                        "sql": None,
                        "dep": name,
                        "state": "extra",
                        "name": name,
                        "disabled": False,
                        "sysNames": [],
                        "highlight": False,
                    }
                )
            upstream_tables += yilai_tables
            focus = "重点检查 SQL 结果表依赖与调度依赖是否一致。"
        else:
            focus = "调度依赖比对不可用（行内库/调度Excel缺失），请人工核对结果表依赖。"

        if job_name:
            job_names.append(job_name)
        py_rows += lint
        py_scripts.append(
            {
                "script": file_name,
                "downloadUrl": download_url(path),
                "table": table_name,
                "job": job_name,
                "jobDisabled": normalize_table(job_name) in disabled_job_names if job_name else False,
                "freq": freq,
                "focus": focus,
                "lint": lint,
                "result": compare_rows,
                "codeval": code_tables,
                "temp": middle_tables,
            }
        )

        seen = {item["name"] for item in ref_tables}
        for names, table_type in ((result_tables, "result"), (code_tables, "src"), (middle_tables, "mid")):
            for name in names:
                if name not in seen:
                    ref_tables.append({"name": name, "type": table_type})
                    seen.add(name)

    upstream_tables = dedupe_tables(upstream_tables)[:16]
    if upstream_tables or job_names:
        deps = [
            {"lane": "上游 / 调度依赖表", "nodes": [{"name": name, "q": ""} for name in upstream_tables]},
            {"lane": "本次作业", "nodes": [{"name": name, "q": "", "focus": True} for name in sorted(set(job_names))]},
        ]
    return py_scripts, py_rows, ref_tables, deps, asset_issues
