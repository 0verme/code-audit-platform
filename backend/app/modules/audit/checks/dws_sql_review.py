"""Shared configurable checks for legacy DWS SQL review markers."""
from __future__ import annotations

from app.config.audit_rules import get_audit_rules


def _configured_matches(sql_text: str) -> tuple[list[str], list[str]]:
    rules = get_audit_rules()["dws"]["sql_review"]
    normalized_sql = str(sql_text or "").upper()
    matched_markers = []
    matched_tables = []

    for item in rules["legacy_markers"]:
        if not isinstance(item, dict):
            continue
        marker = str(item.get("value") or "").strip().upper()
        excludes = [
            str(value).strip().upper()
            for value in item.get("excludes", [])
            if str(value).strip()
        ]
        if marker and marker in normalized_sql and not any(value in normalized_sql for value in excludes):
            matched_markers.append(marker)

    for configured_table in rules["protected_code_tables"]:
        table_name = str(configured_table or "").strip().upper()
        if table_name and table_name in normalized_sql:
            matched_tables.append(table_name)

    return matched_markers, matched_tables


def run_configured_dws_sql_reviews(sql_text: str, *, message_style: str) -> list[str]:
    """Return configured warning messages while preserving each workflow's wording."""
    markers, tables = _configured_matches(sql_text)
    messages = []

    if message_style == "hcyt":
        messages.extend(
            f"建表脚本带{marker},请确认是不是取数单的表名没改"
            for marker in markers
        )
        messages.extend(
            f"存在码值表{table.rsplit('.', 1)[-1]}修改,请审核重点检查"
            for table in tables
        )
        return messages

    if message_style == "nups":
        messages.extend(
            f"建表脚本带 {marker}，请确认是不是取数单的表名没改"
            for marker in markers
        )
        messages.extend(
            f"存在码值表 {table.rsplit('.', 1)[-1]} 修改，请审核重点检查"
            for table in tables
        )
        return messages

    raise ValueError(f"Unsupported DWS SQL review message style: {message_style}")
