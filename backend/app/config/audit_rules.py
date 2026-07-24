"""Strict, cached loading for non-secret audit business rules."""
from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_SCHEMA_VERSION = 1
_LOCK = threading.Lock()
_CACHE: dict[str, Any] | None = None


class AuditRulesConfigError(ValueError):
    """Raised when the audit rules file is missing or invalid."""


class _ValidationError(ValueError):
    pass


def _config_path() -> Path:
    override = os.environ.get("AUDIT_RULES_CONFIG")
    candidate = Path(override).expanduser() if override else Path(__file__).resolve().parents[2] / "configs" / "audit_rules.yaml"
    if candidate.suffix.lower() not in {".yaml", ".yml"}:
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {candidate.resolve()}: "
            "file extension must be .yaml or .yml"
        )
    return candidate


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _ValidationError(f"{path}: expected a mapping")
    if not all(isinstance(key, str) for key in value):
        raise _ValidationError(f"{path}: all keys must be strings")
    return value


def _exact_mapping(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    result = _mapping(value, path)
    missing = sorted(keys - result.keys())
    if missing:
        raise _ValidationError(f"{path}.{missing[0]}: required field is missing")
    unknown = sorted(result.keys() - keys)
    if unknown:
        raise _ValidationError(f"{path}.{unknown[0]}: unknown field")
    return result


def _string(value: Any, path: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise _ValidationError(f"{path}: expected a string")
    if not allow_empty and not value.strip():
        raise _ValidationError(f"{path}: value must not be empty")
    return value


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _ValidationError(f"{path}: expected an integer")
    if minimum is not None and value < minimum:
        raise _ValidationError(f"{path}: value must be at least {minimum}")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise _ValidationError(f"{path}: expected a list")
    return value


def _string_list(value: Any, path: str) -> list[str]:
    result = _list(value, path)
    for index, item in enumerate(result):
        _string(item, f"{path}[{index}]", allow_empty=False)
    return result


def _string_map(value: Any, path: str) -> dict[str, str]:
    result = _mapping(value, path)
    for key, item in result.items():
        _string(key, f"{path} key", allow_empty=False)
        _string(item, f"{path}.{key}")
    return result


def _string_list_map(value: Any, path: str) -> dict[str, list[str]]:
    result = _mapping(value, path)
    for key, item in result.items():
        _string(key, f"{path} key", allow_empty=False)
        _string_list(item, f"{path}.{key}")
    return result


def _validate_schedule(value: Any) -> None:
    path = "hcyt.schedule"
    keys = {
        "real_job_plan_names",
        "invalid_plan_names",
        "recv_mapping_plan_prefix",
        "missing_plan_warning_patterns",
        "plan_name_rules",
        "allowed_domains",
        "disabled_status_values",
        "enabled_status_values",
        "realtime_priority_values",
        "realtime_sequence_keyword",
        "realtime_plan_suffix",
        "realtime_calendar_plans",
        "realtime_calendar_value",
        "forbidden_domain_plan_keywords",
        "forbidden_domain",
        "recv_plan_keyword",
        "provision_job_keyword",
        "sequence_name_rules",
        "dependency_required_job_keywords",
        "dependency_exceptions",
        "late_plan_names",
        "late_plan_exceptions",
        "realtime_dependency_exception",
        "forbidden_dependency_plans",
        "required_predecessors",
        "description_validation",
    }
    schedule = _exact_mapping(value, path, keys)
    for key in {
        "real_job_plan_names",
        "invalid_plan_names",
        "allowed_domains",
        "disabled_status_values",
        "enabled_status_values",
        "realtime_priority_values",
        "realtime_calendar_plans",
        "forbidden_domain_plan_keywords",
        "dependency_required_job_keywords",
        "dependency_exceptions",
        "late_plan_names",
        "late_plan_exceptions",
        "forbidden_dependency_plans",
    }:
        _string_list(schedule[key], f"{path}.{key}")
    for key in {
        "recv_mapping_plan_prefix",
        "realtime_sequence_keyword",
        "realtime_plan_suffix",
        "realtime_calendar_value",
        "forbidden_domain",
        "recv_plan_keyword",
        "provision_job_keyword",
        "realtime_dependency_exception",
    }:
        _string(schedule[key], f"{path}.{key}", allow_empty=False)

    patterns = _list(schedule["missing_plan_warning_patterns"], f"{path}.missing_plan_warning_patterns")
    for index, item in enumerate(patterns):
        item_path = f"{path}.missing_plan_warning_patterns[{index}]"
        pattern = _exact_mapping(item, item_path, {"prefix", "suffix"})
        _string(pattern["prefix"], f"{item_path}.prefix", allow_empty=False)
        _string(pattern["suffix"], f"{item_path}.suffix", allow_empty=False)

    _string_list_map(schedule["plan_name_rules"], f"{path}.plan_name_rules")
    _string_list_map(schedule["sequence_name_rules"], f"{path}.sequence_name_rules")
    _string_list_map(schedule["required_predecessors"], f"{path}.required_predecessors")

    description_path = f"{path}.description_validation"
    description = _exact_mapping(
        schedule["description_validation"],
        description_path,
        {"min_meaningful_chinese_chars", "reference_url", "noise_phrases", "invalid_values"},
    )
    _integer(
        description["min_meaningful_chinese_chars"],
        f"{description_path}.min_meaningful_chinese_chars",
        minimum=1,
    )
    _string(description["reference_url"], f"{description_path}.reference_url")
    _string_list(description["noise_phrases"], f"{description_path}.noise_phrases")
    _string_list(description["invalid_values"], f"{description_path}.invalid_values")


def _validate_dws(value: Any) -> None:
    dws = _exact_mapping(value, "dws", {"naming", "sql_review"})
    naming = _exact_mapping(
        dws["naming"],
        "dws.naming",
        {
            "schema_prefixes",
            "temporary_table_prefixes",
            "comment_required_schemas",
            "root_check_required_schemas",
            "asset_review_required_schemas",
        },
    )
    _string_list_map(naming["schema_prefixes"], "dws.naming.schema_prefixes")
    for key in {
        "temporary_table_prefixes",
        "comment_required_schemas",
        "root_check_required_schemas",
        "asset_review_required_schemas",
    }:
        _string_list(naming[key], f"dws.naming.{key}")

    review = _exact_mapping(dws["sql_review"], "dws.sql_review", {"legacy_markers", "protected_code_tables"})
    markers = _list(review["legacy_markers"], "dws.sql_review.legacy_markers")
    for index, item in enumerate(markers):
        item_path = f"dws.sql_review.legacy_markers[{index}]"
        marker = _exact_mapping(item, item_path, {"value", "excludes"})
        _string(marker["value"], f"{item_path}.value", allow_empty=False)
        _string_list(marker["excludes"], f"{item_path}.excludes")
    _string_list(review["protected_code_tables"], "dws.sql_review.protected_code_tables")


def _validate_fine_report(value: Any) -> None:
    report = _exact_mapping(
        value,
        "fine_report",
        {"file_conventions", "menu_normalization", "sensitive_field_rules"},
    )
    conventions = _exact_mapping(
        report["file_conventions"],
        "fine_report.file_conventions",
        {"menu_filename", "authority_filename", "template_extensions"},
    )
    _string(conventions["menu_filename"], "fine_report.file_conventions.menu_filename", allow_empty=False)
    _string(conventions["authority_filename"], "fine_report.file_conventions.authority_filename", allow_empty=False)
    _string_list(conventions["template_extensions"], "fine_report.file_conventions.template_extensions")

    normalization = _exact_mapping(
        report["menu_normalization"],
        "fine_report.menu_normalization",
        {"required_root_prefix", "replacements"},
    )
    _string(normalization["required_root_prefix"], "fine_report.menu_normalization.required_root_prefix")
    replacements = _list(normalization["replacements"], "fine_report.menu_normalization.replacements")
    for index, item in enumerate(replacements):
        item_path = f"fine_report.menu_normalization.replacements[{index}]"
        replacement = _exact_mapping(item, item_path, {"sources", "replacement", "locations"})
        _string_list(replacement["sources"], f"{item_path}.sources")
        _string(replacement["replacement"], f"{item_path}.replacement")
        _string_list(replacement["locations"], f"{item_path}.locations")
    _string_list_map(report["sensitive_field_rules"], "fine_report.sensitive_field_rules")


def _validate_audit_input(value: Any) -> None:
    audit_input = _exact_mapping(value, "audit_input", {"included_extensions", "file_categories"})
    _string_list(audit_input["included_extensions"], "audit_input.included_extensions")
    categories = _list(audit_input["file_categories"], "audit_input.file_categories")
    for index, item in enumerate(categories):
        item_path = f"audit_input.file_categories[{index}]"
        category = _mapping(item, item_path)
        allowed = {"contains", "suffixes", "category"}
        unknown = sorted(category.keys() - allowed)
        if unknown:
            raise _ValidationError(f"{item_path}.{unknown[0]}: unknown field")
        if "category" not in category:
            raise _ValidationError(f"{item_path}.category: required field is missing")
        if "contains" not in category and "suffixes" not in category:
            raise _ValidationError(f"{item_path}: either contains or suffixes is required")
        _string(category["category"], f"{item_path}.category", allow_empty=False)
        if "contains" in category:
            _string(category["contains"], f"{item_path}.contains", allow_empty=False)
        if "suffixes" in category:
            _string_list(category["suffixes"], f"{item_path}.suffixes")


def _validate_workflows(value: Any) -> None:
    workflows = _exact_mapping(value, "workflows", {"default", "definitions"})
    default = _string(workflows["default"], "workflows.default", allow_empty=False)
    definitions = _list(workflows["definitions"], "workflows.definitions")
    identifiers: set[str] = set()
    for index, item in enumerate(definitions):
        item_path = f"workflows.definitions[{index}]"
        definition = _exact_mapping(item, item_path, {"id", "path_keywords"})
        identifier = _string(definition["id"], f"{item_path}.id", allow_empty=False)
        if identifier in identifiers:
            raise _ValidationError(f"{item_path}.id: duplicate workflow id {identifier!r}")
        identifiers.add(identifier)
        _string_list(definition["path_keywords"], f"{item_path}.path_keywords")
    if default not in identifiers:
        raise _ValidationError("workflows.default: value must match a workflow definition id")


def _validate_source_display_rules(value: Any) -> None:
    rules = _list(value, "source_display_rules")
    for index, item in enumerate(rules):
        item_path = f"source_display_rules[{index}]"
        rule = _exact_mapping(item, item_path, {"sourceType", "prefix", "replacement"})
        for key in {"sourceType", "prefix", "replacement"}:
            _string(rule[key], f"{item_path}.{key}", allow_empty=False)


def _validate_rules(value: Any) -> dict[str, Any]:
    rules = _exact_mapping(
        value,
        "root",
        {
            "schema_version",
            "display",
            "hcyt",
            "dws",
            "nups",
            "fine_report",
            "audit_input",
            "workflows",
            "source_display_rules",
        },
    )
    version = _integer(rules["schema_version"], "schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise _ValidationError(
            f"schema_version: unsupported value {version}; expected {SUPPORTED_SCHEMA_VERSION}"
        )

    display = _exact_mapping(
        rules["display"],
        "display",
        {"highlight_result_source_systems", "calendar_labels"},
    )
    _string_list(display["highlight_result_source_systems"], "display.highlight_result_source_systems")
    _string_map(display["calendar_labels"], "display.calendar_labels")

    hcyt = _exact_mapping(rules["hcyt"], "hcyt", {"schedule"})
    _validate_schedule(hcyt["schedule"])
    _validate_dws(rules["dws"])

    nups = _exact_mapping(rules["nups"], "nups", {"file_rules"})
    file_rules = _exact_mapping(
        nups["file_rules"],
        "nups.file_rules",
        {"sql_filenames", "program_path_patterns", "program_table_name"},
    )
    _string_list(file_rules["sql_filenames"], "nups.file_rules.sql_filenames")
    _string_list(file_rules["program_path_patterns"], "nups.file_rules.program_path_patterns")
    table_name = _exact_mapping(
        file_rules["program_table_name"],
        "nups.file_rules.program_table_name",
        {"directory_schema_prefix"},
    )
    _string(
        table_name["directory_schema_prefix"],
        "nups.file_rules.program_table_name.directory_schema_prefix",
    )

    _validate_fine_report(rules["fine_report"])
    _validate_audit_input(rules["audit_input"])
    _validate_workflows(rules["workflows"])
    _validate_source_display_rules(rules["source_display_rules"])
    return rules


def load_audit_rules(*, path: Path | None = None) -> dict[str, Any]:
    """Load and validate a complete audit rules file."""
    config_path = path or _config_path()
    config_path = config_path.expanduser().resolve()
    if config_path.suffix.lower() not in {".yaml", ".yml"}:
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: "
            "file extension must be .yaml or .yml"
        )
    if not config_path.is_file():
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: file does not exist"
        )
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            supplied = yaml.safe_load(stream)
    except UnicodeDecodeError as exc:
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: file must be valid UTF-8"
        ) from exc
    except OSError as exc:
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f"line {mark.line + 1}, column {mark.column + 1}: " if mark else ""
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: {location}{exc}"
        ) from exc

    try:
        return _validate_rules(supplied)
    except _ValidationError as exc:
        raise AuditRulesConfigError(
            f"Invalid audit rules configuration at {config_path}: {exc}"
        ) from exc


def get_audit_rules() -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _CACHE = load_audit_rules()
        return copy.deepcopy(_CACHE)


def refresh_audit_rules(*, path: Path | None = None) -> dict[str, Any]:
    """Replace the process cache only after a complete file validates."""
    global _CACHE
    loaded = load_audit_rules(path=path)
    with _LOCK:
        _CACHE = loaded
        return copy.deepcopy(_CACHE)
