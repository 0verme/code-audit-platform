from __future__ import annotations

import inspect
import time
from pathlib import Path

from ...shared.findings import CheckResult, finding_messages

def _timed(label, fn, log_timing=None, result_fields=None, **fields):
    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, "start", **fields)
    result = None
    try:
        result = fn()
        return result
    finally:
        if log_timing is not None:
            end_fields = dict(fields)
            if result_fields is not None and result is not None:
                end_fields.update(result_fields(result))
            end_fields["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
            log_timing(label, "end", **end_fields)


def run_hcyt_schedule(
    plan_xls,
    seq_xls,
    cale_xls,
    job_xls,
    *,
    safe,
    modules,
    build_job_table,
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
            result = _timed("schedule.plan.rules", lambda: safe("PLAN 规则", lambda: modules.hcyt.rule_excle_plan(plan_df), CheckResult()), log_timing)
            r_plan = result.artifacts.get("plans")
            plan_rows = finding_messages(result.findings)
            tables["plan"]["messages"] = plan_rows
            rows += [{"table": "PLAN", "item": Path(plan_xls).name, **row} for row in plan_rows]

    if seq_xls:
        seq_source = _timed("schedule.seq.load_excel", lambda: safe("SEQ Excel", lambda: modules.re_service.load_xls_to_df(seq_xls), None), log_timing)
        if seq_source is not None:
            summary["seq"] = len(seq_source)
            seq_df = seq_source.iloc[:, [0, 1, 2]].fillna("")
            seq_df.columns = ["计划名", "作业流名", "作业流描述"]
            tables["seq"] = {"title": "SEQ 作业流清单", **df_table(seq_df)}
            result = _timed("schedule.seq.rules", lambda: safe("SEQ 规则", lambda: modules.hcyt.rule_excle_seq(seq_df), CheckResult()), log_timing)
            seq_rows = finding_messages(result.findings)
            tables["seq"]["messages"] = seq_rows
            rows += [{"table": "SEQ", "item": Path(seq_xls).name, **row} for row in seq_rows]

    if cale_xls:
        cale_source = _timed("schedule.cale.load_excel", lambda: safe("CALE Excel", lambda: modules.re_service.load_xls_to_df(cale_xls), None), log_timing)
        if cale_source is not None:
            tables["cale"] = {"title": "CALE 日历清单", **df_table(cale_source)}

    if job_xls:
        job_source = _timed(
            "schedule.job.load_excel",
            lambda: safe("JOB Excel", lambda: modules.re_service.load_xls_to_df(job_xls), None),
            log_timing,
            result_fields=lambda frame: {"rows": len(frame), "columns": len(frame.columns)},
            file=Path(job_xls).name,
        )
        if job_source is not None:
            summary["job"] = len(job_source)
            job_df = job_source
            db_job_rows = _timed(
                "schedule.job.load_db_jobs",
                lambda: safe("线上作业查询(all_job)", modules.public_data.all_job, None),
                log_timing,
                result_fields=lambda result_rows: {
                    "rows": len(result_rows),
                    "columns": len(result_rows[0]) if result_rows else 0,
                },
            )

            def build_table():
                try:
                    parameters = inspect.signature(build_job_table).parameters.values()
                    supports_timing = any(
                        parameter.name == "timing_log" or parameter.kind == inspect.Parameter.VAR_KEYWORD
                        for parameter in parameters
                    )
                except (TypeError, ValueError):
                    supports_timing = False
                if supports_timing:
                    return build_job_table(job_source, db_job_rows, timing_log=log_timing)
                return build_job_table(job_source, db_job_rows)

            job_table, row_states = _timed(
                "schedule.job.build_table",
                build_table,
                log_timing,
                result_fields=lambda result: {"rows": len(result[0].get("rows", []))},
            )
            tables["job"] = {
                "title": "JOB 作业清单（绿=新增 / 红=禁用再上线）",
                "rowStates": row_states,
                **job_table,
            }
            rule_timing = None
            if log_timing is not None:
                def rule_timing(message):
                    log_timing(
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
                CheckResult(),
            ), log_timing)
            job_rows = _timed(
                "schedule.job.build_messages",
                lambda: finding_messages(result.findings),
                log_timing,
                result_fields=lambda message_rows: {"rows": len(message_rows)},
            )
            tables["job"]["messages"] = job_rows

            def finalize_job_rows():
                rows.extend({"table": "JOB", "item": Path(job_xls).name, **row} for row in job_rows)
                summary["cycles"] = sum(
                    1 for row in job_rows if "成环" in row["msg"] or "循环" in row["msg"]
                )
                summary["missing"] = sum(
                    1 for row in job_rows if ("不存在" in row["msg"] or "未在生产" in row["msg"])
                )

            _timed("schedule.job.finalize_rows", finalize_job_rows, log_timing, rows=len(job_rows))

    return {
        "summary": summary,
        "rows": rows,
        "tables": tables,
        "_job_df": job_df,
        "_r_plan": r_plan,
        "_db_job_rows": db_job_rows,
    }
