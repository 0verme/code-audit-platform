from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd

from .path_export import tail_path


SENSITIVE_VALUE_RE = re.compile(
    r"(?i)(password|passwd|pwd|token|secret|jdbc:|dsn=|://|\b(?:10|127|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)"
)

def merge_job_program(job_df, program_df):
    job_join_col = job_df.columns[4]
    prog_join_col = program_df.columns[1]
    merge_df = job_df.merge(
        program_df,
        left_on=job_join_col,
        right_on=prog_join_col,
        how="inner"
    )
    return merge_df


def build_program_lookup(merge_df, prog_path_col, tail_levels=4):
    if prog_path_col is None:
        raise ValueError("未传入程序路径列名 prog_path_col")
    if prog_path_col not in merge_df.columns:
        raise ValueError(f"程序路径列不存在: {prog_path_col}")

    selected_columns = [merge_df.columns[2], merge_df.columns[9], merge_df.columns[27]]
    path_tails = merge_df[prog_path_col].apply(lambda x: tail_path(x, tail_levels))
    lookup = {}
    for path_tail, row in zip(path_tails, merge_df[selected_columns].itertuples(index=False, name=None)):
        if not path_tail or path_tail in lookup:
            continue
        lookup[path_tail] = list(row)
    return lookup


def get_program_lookup_result(program_lookup, input_path, tail_levels=4):
    input_tail = tail_path(input_path, tail_levels)
    if input_tail in program_lookup:
        return program_lookup[input_tail]
    raise ValueError(f"未找到匹配程序路径: {input_path}")


def _dependency_items(input_string):
    if input_string is None or pd.isna(input_string):
        return []
    return [part[3:] for part in str(input_string).split('|') if part.startswith("33:")]


def get_dependency_items(input_string):
    """Return normalized scheduler dependency job names."""
    return _dependency_items(input_string)


def _table_name_from_program_path_value(path_value):
    p = Path(str(path_value))
    folder = p.parent.name
    if '.' not in folder:
        return None
    schame, table_name = folder.split('.', 1)
    schame = schame.replace('DWS_', '')
    return f'{schame}.{table_name}'


def build_dependency_table_lookup(merge_df):
    dependency_col = merge_df.columns[2]
    program_path_col = merge_df.columns[-6]
    lookup = {}
    for dependency_item, path_value in merge_df[[dependency_col, program_path_col]].itertuples(index=False, name=None):
        if dependency_item in lookup:
            continue
        table_name = _table_name_from_program_path_value(path_value)
        lookup[dependency_item] = table_name if table_name else dependency_item
    return lookup


def build_lineage_row_lookup(merge_df, tail_levels=4):
    """Index merged JOB/PROGRAM rows once for task-local lineage lookups."""
    lookup = {}
    if merge_df is None or getattr(merge_df, "empty", True):
        return lookup
    for row in merge_df.itertuples(index=False, name=None):
        program_path = row[32] if len(row) > 32 else row[-6]
        path_tail = tail_path(program_path, tail_levels)
        if path_tail:
            lookup.setdefault(path_tail, []).append(row)
    return lookup


def get_yilai_table_from_lookup(input_string, dependency_table_lookup):
    matched_values = []
    for item in _dependency_items(input_string):
        table_name = dependency_table_lookup.get(item)
        if table_name:
            matched_values.append(table_name)
    return matched_values


def _safe_lineage_value(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    cleaned = str(value).strip()
    if not cleaned or SENSITIVE_VALUE_RE.search(cleaned):
        return ""
    return cleaned


def _lineage_row_value(row, index=0, field_names=()):
    if row is None:
        return None
    row_mapping = getattr(row, "_mapping", None)
    if hasattr(row_mapping, "keys"):
        for field_name in field_names:
            if field_name in row_mapping:
                return row_mapping[field_name]
        values = list(row_mapping.values())
        return values[index] if index < len(values) else None
    if isinstance(row, dict):
        for field_name in field_names:
            if field_name in row:
                return row[field_name]
        values = list(row.values())
        return values[index] if index < len(values) else None
    if isinstance(row, (str, bytes)):
        return row if index == 0 else None
    for field_name in field_names:
        if hasattr(row, field_name):
            return getattr(row, field_name)
    try:
        return row[index]
    except (TypeError, KeyError, IndexError):
        return row if index == 0 else None


def _dedupe_append(values, value):
    if value and value not in values:
        values.append(value)


def _normalize_lineage_table_name(value):
    cleaned = _safe_lineage_value(value)
    return cleaned.upper() if cleaned else ""


def _normalize_lineage_job_name(value):
    cleaned = _safe_lineage_value(value)
    return cleaned.upper() if cleaned else ""


def _empty_wide_table_lineage_summary(warnings=None):
    return {
        "resultTables": [],
        "jobs": [],
        "recvPlans": [],
        "sysNames": [],
        "outfiles": [],
        "warnings": list(warnings or []),
        "stats": {
            "resultTableCount": 0,
            "jobCount": 0,
            "recvPlanCount": 0,
            "sysNameCount": 0,
            "outfileCount": 0,
        },
        "plan_name": "",
        "job_name": "",
        "program_name": "",
        "program_path": "",
        "result_table": "",
        "dependency_jobs": [],
        "dependency_result_tables": [],
        "recv_plan": "",
        "source_system": "",
        "outfile": "",
        "missing_steps": list(warnings or []),
        "source_fields": [],
    }


def _finalize_wide_table_lineage_summary(summary):
    summary["stats"] = {
        "resultTableCount": len(summary["resultTables"]),
        "jobCount": len(summary["jobs"]),
        "recvPlanCount": len(summary["recvPlans"]),
        "sysNameCount": len(summary["sysNames"]),
        "outfileCount": len(summary["outfiles"]),
    }
    summary["job_name"] = summary["jobs"][0] if summary["jobs"] else ""
    summary["result_table"] = summary["resultTables"][0] if summary["resultTables"] else ""
    summary["dependency_jobs"] = list(summary["jobs"])
    summary["dependency_result_tables"] = list(summary["resultTables"])
    summary["recv_plan"] = summary["recvPlans"][0] if summary["recvPlans"] else ""
    summary["source_system"] = summary["sysNames"][0] if summary["sysNames"] else ""
    summary["outfile"] = summary["outfiles"][0] if summary["outfiles"] else ""
    summary["missing_steps"] = list(summary["warnings"])
    summary["source_fields"] = [
        {"field": "resultTables", "value": list(summary["resultTables"])},
        {"field": "jobs", "value": list(summary["jobs"])},
        {"field": "recvPlans", "value": list(summary["recvPlans"])},
        {"field": "sysNames", "value": list(summary["sysNames"])},
        {"field": "outfiles", "value": list(summary["outfiles"])},
    ]
    return summary


def _safe_metadata_rows(fetcher, warning_name, warnings):
    try:
        return fetcher() or []
    except Exception as exc:
        warnings.append(f"{warning_name} unavailable: {type(exc).__name__}")
        return []


def build_job_outfile_lookup(rows=None):
    lookup = {}
    try:
        iterable = rows or []
    except Exception:
        return lookup

    try:
        for row in iterable:
            job_name = _normalize_lineage_job_name(
                _lineage_row_value(row, 0, ("job_name", "job", "a"))
            )
            outfile = _safe_lineage_value(
                _lineage_row_value(row, 1, ("outfile", "outfile_value", "b"))
            )
            if not job_name or not outfile:
                continue
            if job_name not in lookup:
                lookup[job_name] = outfile
    except Exception:
        return {}
    return lookup


def build_wide_table_lineage_summary(
    merge_df=None,
    input_path=None,
    *,
    job_outfile_lookup=None,
    job_outfile_rows=None,
    result_table_sys_name_rows=None,
    dependency_lookup=None,
    matched_rows=None,
    metadata_service=None,
    tail_levels=4,
    log_timing=None,
):
    def timed(label, fn, **fields):
        started = time.perf_counter()
        if log_timing is not None:
            log_timing(label, "start", **fields)
        try:
            return fn()
        finally:
            if log_timing is not None:
                log_timing(label, "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **fields)

    warnings = []
    summary = _empty_wide_table_lineage_summary()
    summary_seen = {key: set() for key in ("resultTables", "jobs", "recvPlans", "sysNames", "outfiles")}

    def add_summary(key, value):
        if not value or value in summary_seen[key]:
            return
        summary_seen[key].add(value)
        summary[key].append(value)

    if metadata_service is not None:
        if job_outfile_rows is None and job_outfile_lookup is None:
            job_outfile_rows = timed(
                "lineage.summary.query_job_outfiles",
                lambda: _safe_metadata_rows(
                    metadata_service.list_job_outfiles,
                    "job outfile metadata",
                    warnings,
                ),
            )
        if result_table_sys_name_rows is None:
            result_table_sys_name_rows = timed(
                "lineage.summary.query_sys_names",
                lambda: _safe_metadata_rows(
                    metadata_service.list_result_table_sys_names,
                    "result table sys name metadata",
                    warnings,
                ),
            )
    if job_outfile_lookup is None:
        job_outfile_lookup = build_job_outfile_lookup(job_outfile_rows)
    else:
        job_outfile_lookup = {
            _normalize_lineage_job_name(job): _safe_lineage_value(outfile)
            for job, outfile in dict(job_outfile_lookup or {}).items()
            if _normalize_lineage_job_name(job) and _safe_lineage_value(outfile)
        }

    def build_result_table_system_map():
        result_table_system_map = {}
        for row in result_table_sys_name_rows or []:
            table_name = _normalize_lineage_table_name(
                _lineage_row_value(row, 0, ("target_table_name", "table_name", "result_table"))
            )
            sys_name = _safe_lineage_value(
                _lineage_row_value(row, 1, ("system_name", "sys_name", "source_system"))
            )
            if not table_name:
                continue
            result_table_system_map.setdefault(table_name, [])
            if sys_name and sys_name not in result_table_system_map[table_name]:
                result_table_system_map[table_name].append(sys_name)
        return result_table_system_map

    result_table_system_map = timed(
        "lineage.summary.build_result_table_system_map",
        build_result_table_system_map,
        sys_name_rows=len(result_table_sys_name_rows or []),
    )
    scoped_summary = matched_rows is not None or bool(input_path)
    if merge_df is not None or matched_rows is not None:
        try:
            if matched_rows is not None or not getattr(merge_df, "empty", True):
                if matched_rows is None:
                    program_path_col = merge_df.columns[-6]
                    matched_df = merge_df
                    if input_path:
                        input_tail = tail_path(input_path, tail_levels)
                        matched_df = merge_df[
                            merge_df[program_path_col].apply(lambda x: tail_path(x, tail_levels)) == input_tail
                        ]
                    rows_to_iterate = matched_df.itertuples(index=False, name=None)
                    matched_count = len(matched_df.index)
                else:
                    rows_to_iterate = iter(matched_rows)
                    matched_count = len(matched_rows)
                if dependency_lookup is None:
                    dependency_lookup = timed(
                        "lineage.summary.build_dependency_lookup",
                        lambda: build_dependency_table_lookup(merge_df),
                        merge_rows=len(merge_df.index) if merge_df is not None else 0,
                    )
                merge_started = time.perf_counter()
                matched_row_count = 0
                if log_timing is not None:
                    log_timing(
                        "lineage.summary.iterate_merge_rows",
                        "start",
                        merge_rows=len(merge_df.index) if merge_df is not None else matched_count,
                        matched_rows=matched_count,
                    )
                dependency_items_cache = {}
                dependency_tables_cache = {}
                for row in rows_to_iterate:
                    matched_row_count += 1
                    job_name = _normalize_lineage_job_name(row[2] if len(row) > 2 else "")
                    dependency_raw = row[27] if len(row) > 27 else ""
                    program_path = row[32] if len(row) > 32 else row[-6]
                    result_table = _normalize_lineage_table_name(
                        _table_name_from_program_path_value(program_path)
                    )
                    add_summary("jobs", job_name)
                    add_summary("resultTables", result_table)
                    dependency_key = dependency_raw if isinstance(dependency_raw, (str, bytes, type(None))) else str(dependency_raw)
                    if dependency_key not in dependency_items_cache:
                        dependency_items_cache[dependency_key] = _dependency_items(dependency_raw)
                        dependency_tables_cache[dependency_key] = get_yilai_table_from_lookup(
                            dependency_raw, dependency_lookup
                        )
                    for dependency_job in dependency_items_cache[dependency_key]:
                        normalized_job = _normalize_lineage_job_name(dependency_job)
                        add_summary("jobs", normalized_job)
                        add_summary("outfiles", job_outfile_lookup.get(normalized_job, ""))
                    for dependency_table in dependency_tables_cache[dependency_key]:
                        normalized_table = _normalize_lineage_table_name(dependency_table)
                        add_summary("resultTables", normalized_table)
                        for sys_name in result_table_system_map.get(normalized_table, []):
                            add_summary("sysNames", sys_name)
                if log_timing is not None:
                    log_timing(
                        "lineage.summary.iterate_merge_rows",
                        "end",
                        elapsed_ms=round((time.perf_counter() - merge_started) * 1000, 1),
                        merge_rows=len(merge_df.index) if merge_df is not None else matched_count,
                        matched_rows=matched_row_count,
                        jobs=len(summary["jobs"]),
                        result_tables=len(summary["resultTables"]),
                        unique_dependency_values=len(dependency_items_cache),
                    )
        except Exception as exc:
            warnings.append(f"merge metadata unavailable: {type(exc).__name__}")

    if not scoped_summary:
        for table_name, sys_names in result_table_system_map.items():
            add_summary("resultTables", table_name)
            for sys_name in sys_names:
                add_summary("sysNames", sys_name)

        for job_name, outfile in job_outfile_lookup.items():
            add_summary("jobs", job_name)
            add_summary("outfiles", outfile)

    if not any(summary[key] for key in ("resultTables", "jobs", "recvPlans", "sysNames", "outfiles")):
        warnings.append("empty lineage metadata")

    summary["warnings"] = warnings
    return timed(
        "lineage.summary.finalize",
        lambda: _finalize_wide_table_lineage_summary(summary),
        jobs=len(summary["jobs"]),
        result_tables=len(summary["resultTables"]),
        recv_plans=len(summary["recvPlans"]),
        sys_names=len(summary["sysNames"]),
    )
