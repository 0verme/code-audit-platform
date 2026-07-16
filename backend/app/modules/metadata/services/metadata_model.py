"""Validated metadata identifier mappings for profile-specific SQL templates."""
from __future__ import annotations

import logging
import re
from typing import Any

from app.db.profiles import get_metadata_profile, resolve_metadata_profile

LOGGER = logging.getLogger("svn_check.metadata_model")
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

DEFAULT_MODEL = {
    "schema": "dwp",
    "tables": {"jobs": "p_job_hjj", "programs": "p_program_hjj", "plans": "p_plan_hjj", "roles": "p_role_hjj", "fine": "p_fine_hjj", "job_outfiles": "p_job_outfile", "para_tables": "p_para_table_lists", "field_mapping": "p_field_mapping_table", "upstream_system": "p_upstream_system", "recv_dwf": "p_recv_dwf"},
    "columns": {"jobs": {"plan_name": "a", "sequence_name": "b", "job_name": "c", "program_key": "e", "status": "x", "dependencies": "ab"}, "programs": {"program_key": "b", "result_table": "k"}},
}


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid metadata identifier: {label}")
    return value


def get_metadata_model(profile=None) -> dict[str, Any]:
    """Return a safe profile mapping; invalid profile overrides retain defaults."""
    if isinstance(profile, str):
        try:
            profile = resolve_metadata_profile(profile)
        except Exception:
            profile = None
    profile = profile or get_metadata_profile()
    model = dict(DEFAULT_MODEL)
    model["tables"] = dict(DEFAULT_MODEL["tables"])
    model["columns"] = {key: dict(value) for key, value in DEFAULT_MODEL["columns"].items()}
    supplied = profile.config.get("metadata") if getattr(profile, "config", None) else None
    if not supplied:
        return model
    try:
        if not isinstance(supplied, dict):
            raise ValueError("metadata must be a mapping")
        schema = supplied.get("schema", model["schema"])
        model["schema"] = _identifier(schema, "schema")
        for group in ("tables", "columns"):
            value = supplied.get(group, {})
            if not isinstance(value, dict):
                raise ValueError(f"metadata.{group} must be a mapping")
            if group == "tables":
                for key, identifier in value.items():
                    if key in model[group]:
                        model[group][key] = _identifier(identifier, f"tables.{key}")
            else:
                for table, fields in value.items():
                    if table in model[group] and isinstance(fields, dict):
                        for key, identifier in fields.items():
                            if key in model[group][table]:
                                model[group][table][key] = _identifier(identifier, f"columns.{table}.{key}")
        return model
    except ValueError as exc:
        LOGGER.warning("metadata model ignored; using built-in identifiers: %s", exc)
        return {"schema": DEFAULT_MODEL["schema"], "tables": dict(DEFAULT_MODEL["tables"]), "columns": {key: dict(value) for key, value in DEFAULT_MODEL["columns"].items()}}


def table_name(key: str, profile=None) -> str:
    model = get_metadata_model(profile)
    return f"{model['schema']}.{model['tables'][key]}"


def column_name(table: str, key: str, profile=None) -> str:
    return get_metadata_model(profile)["columns"][table][key]
