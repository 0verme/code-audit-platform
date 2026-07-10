from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5


@dataclass(frozen=True)
class AuditAssetIssue:
    issue_key: str
    issue_hash_key: str
    issue_type: str
    issue_title: str
    issue_desc: str
    asset_type: str
    source_module: str
    source_file: str
    severity: str
    suggestion: str
    portal_module: str
    action_label: str
    schema_name: str = ""
    table_name: str = ""
    field_name: str = ""
    root_word: str = ""
    portal_url: str = ""


def _clean_text(value, upper=False):
    if value is None:
        return ""
    text = str(value).strip()
    return text.upper() if upper else text


def _read_issue_value(issue, snake_name, camel_name=None, default=""):
    if isinstance(issue, dict):
        if snake_name in issue:
            return issue.get(snake_name, default)
        if camel_name and camel_name in issue:
            return issue.get(camel_name, default)
        return default
    return getattr(issue, snake_name, default)


def _compact_text(value):
    return "" if value is None else str(value).strip()


def build_issue_key(
    issue_type,
    source_module,
    source_file,
    schema_name="",
    table_name="",
    field_name="",
    root_word="",
):
    parts = [
        _clean_text(issue_type, upper=True),
        _clean_text(source_module, upper=True),
        _clean_text(source_file),
        _clean_text(schema_name, upper=True),
        _clean_text(table_name, upper=True),
        _clean_text(field_name, upper=True),
        _clean_text(root_word, upper=True),
    ]
    return "|".join(parts)


def build_issue_hash_key(issue_key):
    return md5(_clean_text(issue_key).encode("utf-8")).hexdigest()[:12]


def create_audit_asset_issue(
    *,
    issue_type,
    issue_title,
    issue_desc,
    asset_type,
    source_module,
    source_file,
    severity,
    suggestion,
    portal_module,
    action_label,
    schema_name="",
    table_name="",
    field_name="",
    root_word="",
    portal_url="",
):
    issue_key = build_issue_key(
        issue_type=issue_type,
        source_module=source_module,
        source_file=source_file,
        schema_name=schema_name,
        table_name=table_name,
        field_name=field_name,
        root_word=root_word,
    )
    return AuditAssetIssue(
        issue_key=issue_key,
        issue_hash_key=build_issue_hash_key(issue_key),
        issue_type=_clean_text(issue_type, upper=True),
        issue_title=_clean_text(issue_title),
        issue_desc=_clean_text(issue_desc),
        asset_type=_clean_text(asset_type),
        source_module=_clean_text(source_module),
        source_file=_clean_text(source_file),
        severity=_clean_text(severity),
        suggestion=_clean_text(suggestion),
        portal_module=_clean_text(portal_module),
        action_label=_clean_text(action_label),
        schema_name=_clean_text(schema_name, upper=True),
        table_name=_clean_text(table_name, upper=True),
        field_name=_clean_text(field_name, upper=True),
        root_word=_clean_text(root_word, upper=True),
        portal_url=_clean_text(portal_url),
    )


def dedupe_issues(issues):
    deduped = []
    seen = set()
    for issue in issues or []:
        key = getattr(issue, "issue_key", None)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped


def asset_issue_to_unified_issue(issue, scan_batch_id=None, created_at=None):
    rule_code = _compact_text(_read_issue_value(issue, "issue_type", "issueType")).upper()
    issue_key = _compact_text(_read_issue_value(issue, "issue_key", "issueKey"))
    issue_hash_key = _compact_text(_read_issue_value(issue, "issue_hash_key", "hashKey"))
    asset_type = _compact_text(_read_issue_value(issue, "asset_type", "assetType"))
    schema_name = _compact_text(_read_issue_value(issue, "schema_name", "schemaName"))
    table_name = _compact_text(_read_issue_value(issue, "table_name", "tableName"))
    field_name = _compact_text(_read_issue_value(issue, "field_name", "fieldName"))
    root_word = _compact_text(_read_issue_value(issue, "root_word", "rootWord"))
    object_name = _compact_text(_read_issue_value(issue, "object_name", "objectName"))

    stable_key = issue_hash_key or issue_key
    batch_id = _compact_text(scan_batch_id)
    issue_id = f"{batch_id}:{stable_key}" if batch_id and stable_key else stable_key

    if asset_type == "table" and schema_name and table_name:
        asset_key = f"{schema_name}.{table_name}"
    elif asset_type == "root" and root_word:
        asset_key = root_word
    elif asset_type == "field" and schema_name and table_name and field_name:
        asset_key = f"{schema_name}.{table_name}.{field_name}"
    else:
        asset_key = object_name or issue_key

    if asset_type == "table" and schema_name and table_name:
        asset_name = f"{schema_name}.{table_name}"
    elif asset_type == "root" and root_word:
        asset_name = root_word
    else:
        asset_name = object_name or asset_key

    portal_action_map = {
        "ROOT_MISSING": "edit_root",
        "ASSET_TABLE_REVIEW": "review_table",
    }

    return {
        "issue_id": issue_id,
        "scan_batch_id": scan_batch_id,
        "source_system": "",
        "rule_code": rule_code,
        "rule_name": _compact_text(_read_issue_value(issue, "issue_title", "issueTitle")),
        "severity": _compact_text(_read_issue_value(issue, "severity", "severity")) or "warning",
        "asset_type": asset_type,
        "asset_key": asset_key,
        "asset_name": asset_name,
        "portal_module": _compact_text(_read_issue_value(issue, "portal_module", "portalModule")),
        "portal_action": portal_action_map.get(rule_code, "view_detail"),
        "message": _compact_text(_read_issue_value(issue, "issue_desc", "issueDesc")),
        "suggestion": _compact_text(_read_issue_value(issue, "suggestion", "suggestion")),
        "fix_url": _compact_text(_read_issue_value(issue, "portal_url", "portalUrl")),
        "evidence": {
            "issue_key": issue_key,
            "issue_hash_key": issue_hash_key,
            "source_module": _compact_text(_read_issue_value(issue, "source_module", "sourceModule")),
            "source_file": _compact_text(_read_issue_value(issue, "source_file", "sourceFile")),
            "schema_name": schema_name,
            "table_name": table_name,
            "field_name": field_name,
            "root_word": root_word,
            "raw_issue_type": _compact_text(_read_issue_value(issue, "issue_type", "issueType")),
        },
        "created_at": created_at,
    }


def asset_issues_to_unified_issues(asset_issues, scan_batch_id=None, created_at=None):
    return [
        asset_issue_to_unified_issue(issue, scan_batch_id=scan_batch_id, created_at=created_at)
        for issue in asset_issues or []
    ]
