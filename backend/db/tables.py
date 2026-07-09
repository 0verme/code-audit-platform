from __future__ import annotations

from .profiles import DatabaseProfile, resolve_profile


RUNTIME_TABLES = (
    "projects",
    "audit_tasks",
    "task_reports",
    "audit_results",
    "fine_report_items",
)

DEFAULT_RUNTIME_SCHEMA = "dwp"
DEFAULT_TABLE_PREFIX = "p_audit_"
TABLE_TOKEN_PREFIX = "{{table:"
TABLE_TOKEN_SUFFIX = "}}"
SCHEMA_TOKEN = "{{schema}}"

TABLE_NAME_STEMS = {
    "projects": "project_config",
    "audit_tasks": "run",
    "task_reports": "run_report",
    "audit_results": "run_issue",
    "fine_report_items": "fine_report_items",
}

PREFIXED_RUNTIME_TABLES = {
    "projects",
    "audit_tasks",
    "task_reports",
    "audit_results",
}


def _resolve_profile(profile: str | DatabaseProfile | None = None) -> DatabaseProfile:
    if isinstance(profile, DatabaseProfile):
        return profile
    return resolve_profile(profile)


def table_schema(profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    return str(resolved.config.get("schema") or DEFAULT_RUNTIME_SCHEMA).strip()


def table_prefix(profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    return str(resolved.config.get("table_prefix") or DEFAULT_TABLE_PREFIX)


def table_stem(logical_name: str, profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    overrides = dict(resolved.config.get("table_name_stems") or {})
    if logical_name in overrides:
        return str(overrides[logical_name]).strip()
    try:
        return TABLE_NAME_STEMS[logical_name]
    except KeyError as exc:
        raise KeyError(f"Unknown logical runtime table: {logical_name}") from exc


def physical_table_name(logical_name: str, profile: str | DatabaseProfile | None = None) -> str:
    stem = table_stem(logical_name, profile)
    prefix = table_prefix(profile) if logical_name in PREFIXED_RUNTIME_TABLES else ""
    return f"{prefix}{stem}"


def qualified_table_name(logical_name: str, profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    name = physical_table_name(logical_name, resolved)
    schema = table_schema(resolved)
    if not schema:
        return name
    return f"{schema}.{name}"


def render_table_tokens(sql: str, profile: str | DatabaseProfile | None = None) -> str:
    rendered = sql.replace(SCHEMA_TOKEN, table_schema(profile))
    for logical_name in RUNTIME_TABLES:
        rendered = rendered.replace(
            f"{TABLE_TOKEN_PREFIX}{logical_name}{TABLE_TOKEN_SUFFIX}",
            qualified_table_name(logical_name, profile),
        )
    return rendered
