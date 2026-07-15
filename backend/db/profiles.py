from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config_paths import BACKEND_DIR, CONFIG_DIR, DEFAULT_DATABASE_CONFIG, PROJECT_ROOT

DEFAULT_CONFIG_PATH = DEFAULT_DATABASE_CONFIG

CONFIG_PATH_ENV = "AUDIT_DATABASE_CONFIG"
LEGACY_CONFIG_PATH_ENV = "CODE_AUDIT_DB_CONFIG_PATH"
PROFILE_ENV = "CODE_AUDIT_DB_PROFILE"
DEPLOYMENT_MODE_ENV = "CODE_AUDIT_DEPLOYMENT_MODE"
SUPPORTED_TYPES = {"postgresql", "dws"}
REQUIRED_PROFILE_FIELDS = ("type", "host", "port", "database", "username", "password", "schema")
SUPPORTED_TYPES_TEXT = "postgresql, dws"
DEFAULT_RUNTIME_SCHEMA = "dwp"
DEFAULT_TABLE_PREFIX = "p_audit_"


class ProfileConfigError(RuntimeError):
    """Raised when database profile configuration cannot be loaded."""


@dataclass(frozen=True)
class DatabaseProfile:
    name: str
    type: str
    config: dict[str, Any]

    @property
    def is_postgresql(self) -> bool:
        return self.type == "postgresql"

    @property
    def is_dws(self) -> bool:
        return self.type == "dws"


def resolve_config_path(config_path: str | os.PathLike[str] | None = None) -> Path:
    configured = config_path or os.getenv(CONFIG_PATH_ENV) or os.getenv(LEGACY_CONFIG_PATH_ENV)
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return DEFAULT_CONFIG_PATH


def _normalize_database_config(data: dict[str, Any]) -> dict[str, Any]:
    legacy_keys = [key for key in ("backend", "postgres", "defaults") if key in data]
    if legacy_keys:
        raise ProfileConfigError(
            "Database config uses legacy keys "
            f"{', '.join(legacy_keys)}. Use only 'default_profile' and unified 'profiles' entries "
            f"with type in [{SUPPORTED_TYPES_TEXT}]."
        )
    if "profiles" not in data:
        raise ProfileConfigError(
            "Database config must define 'default_profile' and 'profiles' using the unified profile format."
        )

    normalized = dict(data)
    normalized.setdefault("default_profile", None)
    if not isinstance(normalized["profiles"], dict):
        raise ProfileConfigError("Database config 'profiles' must be a mapping")
    return normalized


def _expand_environment_values(value: Any) -> Any:
    """Expand the ${NAME} form used by deploy-time database configuration."""
    if isinstance(value, dict):
        return {key: _expand_environment_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment_values(item) for item in value]
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1], "")
    return value


def _validate_deployment_profile(profile: DatabaseProfile) -> None:
    deployment_mode = os.getenv(DEPLOYMENT_MODE_ENV, "").strip().lower()
    if deployment_mode not in {"inner", "production"}:
        return
    if profile.name != "inner_dws" or profile.type != "dws":
        raise ProfileConfigError(
            f"{DEPLOYMENT_MODE_ENV}={deployment_mode} requires database profile 'inner_dws' with type 'dws'; "
            "refusing to start with another profile."
        )


def load_database_config(config_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = resolve_config_path(config_path)
    if not path.exists():
        override_used = bool(config_path or os.getenv(CONFIG_PATH_ENV) or os.getenv(LEGACY_CONFIG_PATH_ENV))
        source = "an explicit path or environment override" if override_used else "the default location"
        raise ProfileConfigError(
            f"Database config file does not exist: {path} ({source}). "
            f"Copy {CONFIG_DIR / 'database.example.yaml'} to {DEFAULT_CONFIG_PATH}, or set {CONFIG_PATH_ENV} "
            "to an absolute configuration path."
        )

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        raise ProfileConfigError(f"Invalid database config YAML: {path}{location}") from exc
    except OSError as exc:
        raise ProfileConfigError(f"Unable to read database config file: {path}") from exc

    if not isinstance(data, dict):
        raise ProfileConfigError(f"Database config must be a mapping: {path}")

    return _expand_environment_values(_normalize_database_config(data))


def resolve_profile(
    profile_name: str | None = None,
    *,
    config_path: str | os.PathLike[str] | None = None,
) -> DatabaseProfile:
    data = load_database_config(config_path)
    profiles = data["profiles"]
    env_profile_name = os.getenv(PROFILE_ENV)
    selected_name = profile_name or env_profile_name or data.get("default_profile")
    if not selected_name:
        if len(profiles) == 1:
            selected_name = next(iter(profiles))
        else:
            raise ProfileConfigError("Database default_profile is required when multiple profiles are configured")
    selected_name = str(selected_name).strip()
    if selected_name not in profiles:
        available_profiles = ", ".join(sorted(str(name) for name in profiles)) or "<none>"
        source = "argument" if profile_name else PROFILE_ENV if env_profile_name else "default_profile"
        hint = ""
        if selected_name == "profiles":
            hint = (
                f" Hint: '{selected_name}' is the YAML section name, not a profile name. "
                f"Set {PROFILE_ENV} to one of: {available_profiles}"
            )
        raise ProfileConfigError(
            f"Database profile not found: {selected_name} (source: {source}; available: {available_profiles}; "
            f"supported types: [{SUPPORTED_TYPES_TEXT}]).{hint}"
        )

    raw_config = profiles[selected_name]
    if not isinstance(raw_config, dict):
        raise ProfileConfigError(f"Database profile must be a mapping: {selected_name}")

    config = dict(raw_config)
    db_type = str(config.get("type") or "").strip().lower()
    if db_type not in SUPPORTED_TYPES:
        raise ProfileConfigError(
            f"Invalid database profile '{selected_name}': type is {db_type or '<missing>'}; "
            f"supported types are [{SUPPORTED_TYPES_TEXT}]"
        )
    config["type"] = db_type

    missing = [key for key in REQUIRED_PROFILE_FIELDS if not config.get(key)]
    if missing:
        missing_fields = ", ".join(f"profiles.{selected_name}.{key}" for key in missing)
        raise ProfileConfigError(
            f"Invalid database profile '{selected_name}': missing required fields: {missing_fields}; "
            f"supported types are [{SUPPORTED_TYPES_TEXT}]"
        )
    config.setdefault("table_prefix", DEFAULT_TABLE_PREFIX)
    try:
        config["port"] = int(config["port"])
    except (TypeError, ValueError) as exc:
        raise ProfileConfigError(
            f"Invalid database profile '{selected_name}': field 'port' must be an integer; "
            f"supported types are [{SUPPORTED_TYPES_TEXT}]"
        ) from exc
    profile = DatabaseProfile(name=selected_name, type=db_type, config=config)
    _validate_deployment_profile(profile)
    return profile


def get_active_profile() -> DatabaseProfile:
    return resolve_profile()
