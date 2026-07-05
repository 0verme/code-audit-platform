# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping
from typing import Any

from shared.db import router as db_router


logger = logging.getLogger("svn_check.audit_metadata")

DEFAULT_METADATA_PROFILE = "czcb"

TERM_ROOT_SQL = """
SELECT DISTINCT upper(root_code)
FROM dwp.p_term_root
WHERE root_code IS NOT NULL
"""

VIEW_NAME_SQL = """
SELECT upper(table_schema) || '.' || upper(table_name)
FROM information_schema.views
WHERE upper(table_schema) NOT IN ('PG_CATALOG', 'INFORMATION_SCHEMA')
"""

FUNCTION_NAME_SQL = """
SELECT upper(n.nspname) || '.' || upper(p.proname)
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE upper(n.nspname) NOT IN ('PG_CATALOG', 'INFORMATION_SCHEMA')
"""

PARA_TABLE_NAME_SQL = """
select para_table_name
from dwp.p_para_table_lists
"""

JOB_OUTFILE_SQL = """
select a as job_name, b as outfile
from dwp.p_job_outfile
"""

RECV_MAPPING_PLAN_SQL = """
select distinct recv_plan as recv_plan
from dwp.p_recv_ops_mapping
where recv_plan is not null
"""

RESULT_TABLE_SYS_NAME_SQL = """
select d.table_name as table_name, m.sys_name as sys_name
from dwp.p_recv_dwf d
left join dwp.p_recv_ops_mapping m
  on d.recv_plan = m.recv_plan
where d.table_name is not null
"""

RESULT_TABLE_RECV_DETAIL_SQL = """
select d.table_name as table_name, d.recv_plan as recv_plan, m.sys_name as sys_name
from dwp.p_recv_dwf d
left join dwp.p_recv_ops_mapping m
  on d.recv_plan = m.recv_plan
where d.table_name is not null
"""


def _get_metadata_profile_name() -> str:
    return (
        os.getenv("SVN_CHECK_METADATA_PROFILE", "").strip()
        or os.getenv("SVN_CHECK_DB_PROFILE", "").strip()
        or DEFAULT_METADATA_PROFILE
    )


def _get_backend_name() -> str:
    try:
        return str(db_router.get_backend() or "").strip().lower() or "unknown"
    except Exception:
        return "unknown"


def _safe_row_value(row: Any, index: int = 0, field_names: tuple[str, ...] = ()) -> Any:
    if row is None:
        return None
    row_mapping = getattr(row, "_mapping", None)
    if isinstance(row_mapping, Mapping):
        for field_name in field_names:
            if field_name in row_mapping:
                return row_mapping[field_name]
        values = list(row_mapping.values())
        return values[index] if index < len(values) else None
    if isinstance(row, Mapping):
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


def _normalize_value(value: Any, upper: bool = False) -> str:
    normalized = "" if value is None else str(value).strip()
    return normalized.upper() if upper else normalized


def _normalize_single_column_rows(
    rows: Iterable[Any] | None,
    upper: bool = True,
    field_names: tuple[str, ...] = (),
) -> list[tuple[str]]:
    result: list[tuple[str]] = []
    seen: set[str] = set()
    for row in rows or []:
        value = _normalize_value(_safe_row_value(row, 0, field_names), upper=upper)
        if value and value not in seen:
            seen.add(value)
            result.append((value,))
    return result


def _normalize_multi_column_rows(
    rows: Iterable[Any] | None,
    columns: tuple[tuple[str, ...], ...],
) -> list[tuple[str, ...]]:
    result: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for row in rows or []:
        values = tuple(
            _normalize_value(_safe_row_value(row, index, field_names))
            for index, field_names in enumerate(columns)
        )
        if any(values) and values not in seen:
            seen.add(values)
            result.append(values)
    return result


def _run_metadata_query(sql: str, function_name: str) -> list[Any]:
    profile = _get_metadata_profile_name()
    backend = _get_backend_name()
    try:
        rows = db_router.select_sql_with_profile(profile, sql)
        return rows or []
    except Exception as exc:
        logger.warning(
            "audit metadata query degraded profile=%s backend=%s function=%s error=%s",
            profile,
            backend,
            function_name,
            type(exc).__name__,
        )
        return []


def list_term_roots() -> list[tuple[str]]:
    return _normalize_single_column_rows(_run_metadata_query(TERM_ROOT_SQL, "list_term_roots"))


def list_view_names() -> list[tuple[str]]:
    return _normalize_single_column_rows(_run_metadata_query(VIEW_NAME_SQL, "list_view_names"))


def list_function_names() -> list[tuple[str]]:
    return _normalize_single_column_rows(_run_metadata_query(FUNCTION_NAME_SQL, "list_function_names"))


def list_para_table_names() -> list[tuple[str]]:
    return _normalize_single_column_rows(_run_metadata_query(PARA_TABLE_NAME_SQL, "list_para_table_names"))


def list_job_outfiles() -> list[tuple[str, str]]:
    return _normalize_multi_column_rows(
        _run_metadata_query(JOB_OUTFILE_SQL, "list_job_outfiles"),
        (
            ("job_name", "a", "job"),
            ("outfile", "b", "outfile_value"),
        ),
    )


def list_recv_mapping_plans() -> list[tuple[str]]:
    return _normalize_single_column_rows(
        _run_metadata_query(RECV_MAPPING_PLAN_SQL, "list_recv_mapping_plans"),
        field_names=("recv_plan", "plan"),
    )


def list_result_table_sys_names() -> list[tuple[str, str]]:
    return _normalize_multi_column_rows(
        _run_metadata_query(RESULT_TABLE_SYS_NAME_SQL, "list_result_table_sys_names"),
        (
            ("table_name", "result_table", "d.table_name"),
            ("sys_name", "source_system", "m.sys_name"),
        ),
    )


def list_result_table_recv_details() -> list[tuple[str, str, str]]:
    return _normalize_multi_column_rows(
        _run_metadata_query(RESULT_TABLE_RECV_DETAIL_SQL, "list_result_table_recv_details"),
        (
            ("table_name", "result_table", "d.table_name"),
            ("recv_plan", "plan", "d.recv_plan"),
            ("sys_name", "source_system", "m.sys_name"),
        ),
    )
