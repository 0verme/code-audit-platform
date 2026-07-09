from __future__ import annotations

from pathlib import Path


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
        plan_source = safe("PLAN Excel", lambda: modules.re_service.load_xls_to_df(plan_xls), None)
        if plan_source is not None:
            summary["plan"] = len(plan_source)
            plan_df = plan_source.iloc[:, [0, 4]].fillna("")
            plan_df.columns = ["计划名", "前置依赖"]
            tables["plan"] = {"title": "PLAN 计划清单", **df_table(plan_df)}
            result = safe("PLAN 规则", lambda: modules.hcyt.rule_excle_plan(plan_df), ("", "", 0, None))
            r_plan = result[3] if len(result) > 3 else None
            plan_rows = schedule_rows_fn(result[0], result[1])
            tables["plan"]["messages"] = plan_rows
            rows += [{"table": "PLAN", "item": Path(plan_xls).name, **row} for row in plan_rows]

    if seq_xls:
        seq_source = safe("SEQ Excel", lambda: modules.re_service.load_xls_to_df(seq_xls), None)
        if seq_source is not None:
            summary["seq"] = len(seq_source)
            seq_df = seq_source.iloc[:, [0, 1, 2]].fillna("")
            seq_df.columns = ["计划名", "作业流名", "作业流描述"]
            tables["seq"] = {"title": "SEQ 作业流清单", **df_table(seq_df)}
            result = safe("SEQ 规则", lambda: modules.hcyt.rule_excle_seq(seq_df), ("", "", 0))
            seq_rows = schedule_rows_fn(result[0], result[1])
            tables["seq"]["messages"] = seq_rows
            rows += [{"table": "SEQ", "item": Path(seq_xls).name, **row} for row in seq_rows]

    if cale_xls:
        cale_source = safe("CALE Excel", lambda: modules.re_service.load_xls_to_df(cale_xls), None)
        if cale_source is not None:
            tables["cale"] = {"title": "CALE 日历清单", **df_table(cale_source)}

    if job_xls:
        job_source = safe("JOB Excel", lambda: modules.re_service.load_xls_to_df(job_xls), None)
        if job_source is not None:
            summary["job"] = len(job_source)
            job_df = job_source
            db_job_rows = safe("线上作业查询(all_job)", modules.public_data.all_job, None)
            job_table, row_states = build_job_table(job_source, db_job_rows)
            tables["job"] = {
                "title": "JOB 作业清单（绿=新增 / 红=禁用再上线）",
                "rowStates": row_states,
                **job_table,
            }
            result = safe(
                "JOB 规则",
                lambda: modules.hcyt.rule_excle_job(job_df, r_plan=r_plan, timing_log=None, job_rows=db_job_rows),
                ("", "", 0),
            )
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
