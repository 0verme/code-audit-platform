# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import json
import os
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib import error, request

from app.db.metadata.compat import router as db_router
from app.db.profiles import get_active_profile


logger = logging.getLogger("svn_check.audit_metadata")

ASSET_PORTAL_BASE_URL_ENV = "ASSET_PORTAL_BASE_URL"
ASSET_PORTAL_API_TOKEN_ENV = "ASSET_PORTAL_API_TOKEN"
ASSET_PORTAL_ROOT_CACHE_FILE_ENV = "ASSET_PORTAL_ROOT_CACHE_FILE"
ASSET_PORTAL_ROOT_CACHE_TTL_SECONDS_ENV = "ASSET_PORTAL_ROOT_CACHE_TTL_SECONDS"
ASSET_PORTAL_ROOT_TIMEOUT_SECONDS_ENV = "ASSET_PORTAL_ROOT_TIMEOUT_SECONDS"

_term_root_memory_cache: tuple[float, list[tuple[str]]] | None = None

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
    return get_active_profile().name


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


def _asset_portal_root_url() -> str:
    base_url = os.getenv(ASSET_PORTAL_BASE_URL_ENV, "").strip().rstrip("/")
    return f"{base_url}/api/roots" if base_url else ""


def _root_cache_ttl_seconds() -> float:
    try:
        return max(0.0, float(os.getenv(ASSET_PORTAL_ROOT_CACHE_TTL_SECONDS_ENV, "300")))
    except ValueError:
        return 300.0


def _read_root_snapshot() -> list[tuple[str]]:
    raw_path = os.getenv(ASSET_PORTAL_ROOT_CACHE_FILE_ENV, "").strip()
    if not raw_path:
        return []
    try:
        payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return _normalize_single_column_rows(payload.get("roots") if isinstance(payload, dict) else payload)


def _write_root_snapshot(roots: list[tuple[str]]) -> None:
    raw_path = os.getenv(ASSET_PORTAL_ROOT_CACHE_FILE_ENV, "").strip()
    if not raw_path:
        return
    try:
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"roots": [root[0] for root in roots]}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        logger.warning("asset portal term-root snapshot write failed")


def _fetch_asset_portal_term_roots() -> list[tuple[str]]:
    url = _asset_portal_root_url()
    if not url:
        raise RuntimeError("asset portal API is not configured")
    headers = {"Accept": "application/json"}
    token = os.getenv(ASSET_PORTAL_API_TOKEN_ENV, "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        timeout = float(os.getenv(ASSET_PORTAL_ROOT_TIMEOUT_SECONDS_ENV, "10"))
    except ValueError:
        timeout = 10.0
    try:
        with request.urlopen(request.Request(url, headers=headers), timeout=max(0.1, timeout)) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, error.HTTPError, error.URLError) as exc:
        raise RuntimeError(type(exc).__name__) from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("items"), list):
        raise RuntimeError("invalid asset portal root response")
    return _normalize_single_column_rows(payload["items"], field_names=("abbr", "root_code", "rootCode"))


def list_term_roots() -> list[tuple[str]]:
    global _term_root_memory_cache
    now = time.monotonic()
    if _term_root_memory_cache and now - _term_root_memory_cache[0] <= _root_cache_ttl_seconds():
        return _term_root_memory_cache[1]
    try:
        roots = _fetch_asset_portal_term_roots()
    except Exception as exc:
        cached_roots = _term_root_memory_cache[1] if _term_root_memory_cache else _read_root_snapshot()
        logger.warning("asset portal term-root query degraded error=%s cache=%s", type(exc).__name__, bool(cached_roots))
        return cached_roots
    _term_root_memory_cache = (now, roots)
    _write_root_snapshot(roots)
    return roots


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
