from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.db.profiles import get_metadata_profile
from app.db.sql_runner import SQLRunner


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELDS = ("id", "type", "owner", "title", "status", "date", "time", "source", "remark", "detail_url")
_REQUIRED_FIELDS = ("id", "title", "status", "date")
_COLUMN_CANDIDATES = {
    "id": ("taskid", "requirement_id", "requirementid", "req_id", "reqid", "demand_id", "id"),
    "type": ("tasktype", "requirement_type", "req_type", "demand_type", "type"),
    "owner": ("taskuer", "taskuser", "developer", "developer_name", "owner", "creator", "created_by", "submitter"),
    "title": ("tasktitle", "requirement_title", "req_title", "demand_title", "title", "name"),
    "status": ("taskstatus", "publish_status", "review_status", "status", "state"),
    "date": ("taskdate", "planned_publish_date", "plan_publish_date", "publish_date", "release_date", "online_date"),
    "time": ("planned_publish_time", "plan_publish_time", "publish_time", "release_time", "online_time"),
    "source": ("tasksource", "source", "source_system", "origin"),
    "remark": ("taskremark", "remark", "remarks", "description"),
    "detail_url": ("detail_url", "url", "link"),
}
_STATUS_ALIASES = {
    "pending": "pending", "待审核": "pending", "待审查": "pending", "生产待审": "pending", "运行待审": "pending", "开发待审": "pending", "0": "pending",
    "reviewing": "reviewing", "审核中": "reviewing", "审查中": "reviewing", "1": "reviewing",
    "passed": "passed", "approved": "passed", "已通过": "passed", "等待上线": "passed", "2": "passed",
    "rejected": "rejected", "已驳回": "rejected", "驳回": "rejected", "3": "rejected",
    "launched": "launched", "published": "launched", "已上线": "launched", "已发布": "launched", "4": "launched",
}


class PublishListConfigurationError(RuntimeError):
    pass


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise PublishListConfigurationError(f"Invalid publish-list identifier: {label}")
    return value


def _configured_model(profile: Any) -> tuple[str, str, dict[str, str]]:
    metadata = profile.config.get("metadata") or {}
    schema = _identifier(metadata.get("schema") or profile.config.get("schema") or "dwp", "schema")
    tables = metadata.get("tables") or {}
    table = _identifier(tables.get("publish_list") or "p_publishlist", "table")
    supplied = (metadata.get("columns") or {}).get("publish_list") or {}
    if not isinstance(supplied, dict):
        raise PublishListConfigurationError("metadata.columns.publish_list must be a mapping")
    columns = {field: _identifier(value, f"columns.publish_list.{field}") for field, value in supplied.items() if field in _FIELDS}
    return schema, table, columns


def _resolve_columns(runner: SQLRunner, schema: str, table: str, configured: dict[str, str]) -> dict[str, str]:
    rows = runner.query_all(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        (schema, table),
    )
    available = {str(row["column_name"]).lower(): str(row["column_name"]) for row in rows}
    if not available:
        raise PublishListConfigurationError(f"Publish-list table is not visible: {schema}.{table}")

    resolved: dict[str, str] = {}
    for field in _FIELDS:
        explicit = configured.get(field)
        if explicit:
            actual = available.get(explicit.lower())
            if not actual:
                raise PublishListConfigurationError(f"Configured publish-list column is missing: {field}")
            resolved[field] = _identifier(actual, field)
            continue
        for candidate in _COLUMN_CANDIDATES[field]:
            if candidate.lower() in available:
                resolved[field] = _identifier(available[candidate.lower()], field)
                break

    missing = [field for field in _REQUIRED_FIELDS if field not in resolved]
    if missing:
        raise PublishListConfigurationError(
            "Publish-list field mapping is incomplete: " + ", ".join(missing)
        )
    return resolved


def _iso_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip()
    return _STATUS_ALIASES.get(text.lower(), _STATUS_ALIASES.get(text, "unknown"))


def _safe_detail_url(value: Any) -> str:
    text = _iso_value(value).strip()
    if text.startswith(("https://", "http://")):
        return text
    if text.startswith("/") and not text.startswith("//"):
        return text
    return ""


def get_publish_list(selected_date: date, *, profile: Any = None, runner: SQLRunner | None = None) -> dict[str, Any]:
    profile = profile or get_metadata_profile()
    runner = runner or SQLRunner(profile)
    schema, table, configured = _configured_model(profile)
    columns = _resolve_columns(runner, schema, table, configured)

    select_parts = []
    for field in _FIELDS:
        column = columns.get(field)
        select_parts.append(f"{column} AS {field}" if column else f"NULL AS {field}")
    order_column = columns.get("time") or columns["id"]
    sql = (
        f"SELECT {', '.join(select_parts)} FROM {schema}.{table} "
        f"WHERE CAST({columns['date']} AS DATE) = ? ORDER BY {order_column}, {columns['id']} LIMIT 1000"
    )
    rows = runner.query_all(sql, (selected_date.isoformat(),))
    items = [
        {
            "id": _iso_value(row.get("id")),
            "type": _iso_value(row.get("type")),
            "owner": _iso_value(row.get("owner")),
            "title": _iso_value(row.get("title")),
            "status": _normalize_status(row.get("status")),
            "statusLabel": _iso_value(row.get("status")),
            "date": _iso_value(row.get("date"))[:10],
            "time": _iso_value(row.get("time")),
            "source": _iso_value(row.get("source")),
            "remark": _iso_value(row.get("remark")),
            "detailUrl": _safe_detail_url(row.get("detail_url")),
        }
        for row in rows
    ]
    summary = {key: 0 for key in ("pending", "reviewing", "passed", "rejected", "launched", "unknown")}
    for item in items:
        summary[item["status"]] += 1
    summary["total"] = len(items)
    return {"date": selected_date.isoformat(), "items": items, "summary": summary, "truncated": len(items) == 1000}
