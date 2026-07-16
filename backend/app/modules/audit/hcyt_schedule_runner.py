from __future__ import annotations

import time
from pathlib import Path


def _timed(label, fn, log_timing=None, **fields):
    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, "start", **fields)
    try:
        return fn()
    finally:
        if log_timing is not None:
            log_timing(label, "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **fields)


def schedule_rows(result_text, warn_text, *, rule_label):
    rows = []
    for raw, level in ((result_text, "err"), (warn_text, "warn")):
        if not raw or not isinstance(raw, str):
            continue
        for line in raw.split("\n"):
            line = line.strip()
            if line:
                rows.append({"rule": rule_label(line), "level": level, "msg": line})
    return rows


def run_hcyt_schedule(
    plan_xls,
    seq_xls,
    cale_xls,
    job_xls,
    *,
    safe,
    modules,
    build_job_table,
    schedule_rows_fn,
    log_timing=None,
):
    rows = []
    tables = {}
    summary = {"plan": 0, "seq": 0, "job": 0, "cycles": 0, "missing": 0}
    job_df = r_plan = db_job_rows = None

    def df_table(df, columns=None):
        display = df.fillna("") if df is not None else None
        if display is None:
            return {"columns": [], "rows": []}
        cols = columns or [str(c) for c in display.columns]
        return {"columns": cols, "rows": display.astype(str).values.tolist()}

    if plan_xls:
        plan_source = _timed("schedule.plan.load_excel", lambda: safe("PLAN Excel", lambda: modules.re_service.load_xls_to_df(plan_xls), None), log_timing)
        if plan_source is not None:
            summary["plan"] = len(plan_source)
            plan_df = plan_source.iloc[:, [0, 4]].fillna("")
            plan_df.columns = ["计划名", "前置依赖"]
            tables["plan"] = {"title": "PLAN 计划清单", **df_table(plan_df)}
            result = _timed("schedule.plan.rules", lambda: safe("PLAN 规则", lambda: modules.hcyt.rule_excle_plan(plan_df), ("", "", 0, None)), log_timing)
            r_plan = result[3] if len(result) > 3 else None
            plan_rows = schedule_rows_fn(result[0], result[1])
            tables["plan"]["messages"] = plan_rows
            rows += [{"table": "PLAN", "item": Path(plan_xls).name, **row} for row in plan_rows]

    if seq_xls:
        seq_source = _timed("schedule.seq.load_excel", lambda: safe("SEQ Excel", lambda: modules.re_service.load_xls_to_df(seq_xls), None), log_timing)
        if seq_source is not None:
            summary["seq"] = len(seq_source)
            seq_df = seq_source.iloc[:, [0, 1, 2]].fillna("")
            seq_df.columns = ["计划名", "作业流名", "作业流描述"]
            tables["seq"] = {"title": "SEQ 作业流清单", **df_table(seq_df)}
            result = _timed("schedule.seq.rules", lambda: safe("SEQ 规则", lambda: modules.hcyt.rule_excle_seq(seq_df), ("", "", 0)), log_timing)
            seq_rows = schedule_rows_fn(result[0], result[1])
            tables["seq"]["messages"] = seq_rows
            rows += [{"table": "SEQ", "item": Path(seq_xls).name, **row} for row in seq_rows]

    if cale_xls:
        cale_source = _timed("schedule.cale.load_excel", lambda: safe("CALE Excel", lambda: modules.re_service.load_xls_to_df(cale_xls), None), log_timing)
        if cale_source is not None:
            tables["cale"] = {"title": "CALE 日历清单", **df_table(cale_source)}

    if job_xls:
        job_source = _timed("schedule.job.load_excel", lambda: safe("JOB Excel", lambda: modules.re_service.load_xls_to_df(job_xls), None), log_timing)
        if job_source is not None:
            summary["job"] = len(job_source)
            job_df = job_source
            db_job_rows = _timed("schedule.job.load_db_jobs", lambda: safe("线上作业查询(all_job)", modules.public_data.all_job, None), log_timing)
            job_table, row_states = _timed("schedule.job.build_table", lambda: build_job_table(job_source, db_job_rows), log_timing)
            tables["job"] = {
                "title": "JOB 作业清单（绿=新增 / 红=禁用再上线）",
                "rowStates": row_states,
                **job_table,
            }
            rule_timing = None
            if log_timing is not None:
                rule_timing = lambda message: log_timing(
                    "schedule.job.rules.detail",
                    "point",
                    message=message,
                )
            result = _timed("schedule.job.rules", lambda: safe(
                "JOB 规则",
                lambda: modules.hcyt.rule_excle_job(
                    job_df,
                    r_plan=r_plan,
                    timing_log=rule_timing,
                    job_rows=db_job_rows,
                ),
                ("", "", 0),
            ), log_timing)
            job_rows = schedule_rows_fn(result[0], result[1])
            tables["job"]["messages"] = job_rows
            rows += [{"table": "JOB", "item": Path(job_xls).name, **row} for row in job_rows]
            summary["cycles"] = sum(1 for row in job_rows if "成环" in row["msg"] or "循环" in row["msg"])
            summary["missing"] = sum(
                1 for row in job_rows if ("不存在" in row["msg"] or "未在生产" in row["msg"])
            )

    return {
        "summary": summary,
        "rows": rows,
        "tables": tables,
        "_job_df": job_df,
        "_r_plan": r_plan,
        "_db_job_rows": db_job_rows,
    }
