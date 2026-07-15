from __future__ import annotations

import time


def _run_timed(label, fn, log_timing=None):
    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, "start")
    try:
        return fn()
    finally:
        if log_timing is not None:
            log_timing(label, "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1))


def run_hcyt_rules(
    dws_url,
    hive_url,
    schame_config_lists,
    sbin_lists,
    recv_lists,
    dwo_lists,
    dwf_lists,
    *,
    safe,
    modules,
    grouped,
    task_running,
    task_success,
    task_skipped,
    set_partial,
    download_url,
    build_config_files,
    log_timing=None,
):
    sql_checks = {}
    asset_issues = []
    config_files = []

    if dws_url:
        task_running("dws_sql")
        result = _run_timed("rules.dws_sql", lambda: safe("dws.sql 规则", lambda: modules.hcyt.rule_dws(dws_url), ("", "", 0)), log_timing)
        grouped["dws"] += modules.text_to_rows(
            result[0],
            result[1],
            modules.re_service.get_filename(dws_url),
            warn_level="info",
        )
        sql_checks["dws"] = {
            "script": modules.re_service.get_filename(dws_url),
            "downloadUrl": download_url(dws_url),
        }
        set_partial("sqlChecks", dict(sql_checks))
        dws_file_name = modules.re_service.get_filename(dws_url)
        dws_sql_text = _run_timed("rules.dws_sql.read", lambda: safe("dws.sql 内容读取", lambda: modules.re_service.read_data_from_file(dws_url), ""), log_timing)
        asset_issues += safe(
            "dws.sql 词根结构化 issue",
            lambda: modules.hcyt_ddl_rule.collect_root_missing_issues(dws_sql_text, "hcyt", dws_file_name),
            [],
        )
        asset_issues += safe(
            "dws.sql 资产表待核对 issue",
            lambda: modules.hcyt_sql_rule.collect_created_table_review_issues(dws_url, "hcyt", dws_file_name),
            [],
        )
        set_partial("dws", grouped["dws"])
        task_success("dws_sql", result=grouped["dws"], summary={"issues": len(grouped["dws"])})
    else:
        task_skipped("dws_sql", "no dws.sql file")

    if hive_url:
        task_running("hive_sql")
        result = _run_timed("rules.hive_sql", lambda: safe("hive.sql 规则", lambda: modules.hcyt.rule_hive(hive_url), ("", "", 0)), log_timing)
        grouped["hive"] += modules.text_to_rows(
            result[0],
            result[1],
            modules.re_service.get_filename(hive_url),
            warn_level="info",
        )
        sql_checks["hive"] = {
            "script": modules.re_service.get_filename(hive_url),
            "downloadUrl": download_url(hive_url),
        }
        set_partial("sqlChecks", dict(sql_checks))
        set_partial("hive", grouped["hive"])
        task_success("hive_sql", result=grouped["hive"], summary={"issues": len(grouped["hive"])})
    else:
        task_skipped("hive_sql", "no hive.sql file")

    if sbin_lists:
        task_running("post_scripts")
        result = _run_timed("rules.post_scripts", lambda: safe("sbin 规则", lambda: modules.hcyt.rule_sbin(sbin_lists), ("", "", 0)), log_timing)
        grouped["sbin"] += modules.text_to_rows(result[0], result[1], "sbin")
        set_partial("sbin", grouped["sbin"])
        task_success("post_scripts", result=grouped["sbin"], summary={"issues": len(grouped["sbin"])})
    else:
        task_skipped("post_scripts", "no post script files")

    if recv_lists:
        task_running("recv_config")
        result = _run_timed("rules.recv_config", lambda: safe("recv 卸数规则", lambda: modules.hcyt.rule_recv_json(recv_lists), ("", "", 0)), log_timing)
        grouped["recv"] += modules.text_to_rows(result[0], result[1], "recv_json")
        set_partial("recv", grouped["recv"])
        task_success("recv_config", result=grouped["recv"], summary={"issues": len(grouped["recv"])})
    else:
        task_skipped("recv_config", "no recv config files")

    if schame_config_lists:
        task_running("config_files")
        result = _run_timed("rules.config_files", lambda: safe("schema_config 规则", lambda: modules.hcyt.rule_config(schame_config_lists), ("", "", 0)), log_timing)
        grouped["config"] += modules.text_to_rows(result[0], result[1], "SCHEMA_CONFIG", err_level="warn")
        config_files = build_config_files(schame_config_lists)
        set_partial("config", grouped["config"])
        set_partial("configFiles", config_files)
        task_success("config_files", result=grouped["config"], summary={"issues": len(grouped["config"])})
    else:
        task_skipped("config_files", "no schema config files")

    for path in dwo_lists or []:
        result = _run_timed("rules.dwo", lambda p=path: safe("dwo 规则", lambda: modules.hcyt.rule_dwo(p), ("", "", 0)), log_timing)
        grouped["python"] += modules.text_to_rows(result[0], result[1], modules.re_service.get_filename(path))
    for path in dwf_lists or []:
        result = _run_timed("rules.dwf", lambda p=path: safe("dwf 规则", lambda: modules.hcyt.rule_dwf(p), ("", "", 0)), log_timing)
        grouped["python"] += modules.text_to_rows(result[0], result[1], modules.re_service.get_filename(path))

    return sql_checks, asset_issues, config_files
