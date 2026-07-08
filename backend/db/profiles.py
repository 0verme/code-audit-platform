from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = BACKEND_DIR / "svn_check" / "configs" / "database.yaml"

CONFIG_PATH_ENV = "CODE_AUDIT_DB_CONFIG_PATH"
PROFILE_ENV = "CODE_AUDIT_DB_PROFILE"
SUPPORTED_TYPES = {"sqlite", "postgresql", "dws"}


class ProfileConfigError(RuntimeError):
    """Raised when database profile configuration cannot be loaded."""


@dataclass(frozen=True)
class DatabaseProfile:
    name: str
    type: str
    config: dict[str, Any]

    @property
    def is_sqlite(self) -> bool:
        return self.type == "sqlite"

    @property
    def is_postgresql(self) -> bool:
        return self.type == "postgresql"

    @property
    def is_dws(self) -> bool:
        return self.type == "dws"


def resolve_config_path(config_path: str | os.PathLike[str] | None = None) -> Path:
    configured = config_path or os.getenv(CONFIG_PATH_ENV)
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_ROOT / path
    return DEFAULT_CONFIG_PATH


def _runtime_profile_from_postgres_block(data: dict[str, Any]) -> dict[str, Any] | None:
    backend = (os.getenv("SVN_CHECK_DB_BACKEND") or data.get("backend") or "").strip().lower()
    if backend != "postgres":
        return None

    postgres = dict(data.get("postgres") or {})
    overrides = {
        "host": "SVN_CHECK_PG_HOST",
        "port": "SVN_CHECK_PG_PORT",
        "dbname": "SVN_CHECK_PG_DB",
        "user": "SVN_CHECK_PG_USER",
        "password": "SVN_CHECK_PG_PASSWORD",
        "schema": "SVN_CHECK_PG_SCHEMA",
    }
    for key, env_name in overrides.items():
        value = os.getenv(env_name)
        if value:
            postgres[key] = value

    return {
        "type": "postgresql",
        "host": postgres.get("host"),
        "port": postgres.get("port"),
        "database": postgres.get("dbname") or postgres.get("database"),
        "username": postgres.get("user") or postgres.get("username"),
        "password": postgres.get("password"),
        "schema": postgres.get("schema", "public"),
        "connect_timeout": postgres.get("connect_timeout", 30),
    }


def _normalize_database_config(data: dict[str, Any]) -> dict[str, Any]:
    runtime_profile = _runtime_profile_from_postgres_block(data)
    if runtime_profile:
        profiles = dict(data.get("profiles") or {})
        profiles["postgres"] = runtime_profile
        return {
            "default_profile": data.get("default_profile") or "postgres",
            "profiles": profiles,
        }

    if "profiles" in data:
        data.setdefault("default_profile", None)
        data.setdefault("profiles", {})
        if not isinstance(data["profiles"], dict):
            raise ProfileConfigError("Database config 'profiles' must be a mapping")
        return data

    raise ProfileConfigError(
        "Database config must define profiles or set backend: postgres with a postgres block: "
        f"{DEFAULT_CONFIG_PATH}"
    )


def load_database_config(config_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = resolve_config_path(config_path)
    explicit_path = bool(config_path or os.getenv(CONFIG_PATH_ENV))
    if not path.exists():
        if explicit_path:
            raise ProfileConfigError(f"Database config file does not exist: {path}")
        raise ProfileConfigError(f"Database config file does not exist: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ProfileConfigError(f"Invalid database config YAML: {path}") from exc
    except OSError as exc:
        raise ProfileConfigError(f"Unable to read database config file: {path}") from exc

    if not isinstance(data, dict):
        raise ProfileConfigError(f"Database config must be a mapping: {path}")

    return _normalize_database_config(data)


def resolve_profile(
    profile_name: str | None = None,
    *,
    config_path: str | os.PathLike[str] | None = None,
) -> DatabaseProfile:
    data = load_database_config(config_path)
    profiles = data["profiles"]
    selected_name = profile_name or os.getenv(PROFILE_ENV) or data.get("default_profile")
    if not selected_name:
        if len(profiles) == 1:
            selected_name = next(iter(profiles))
        else:
            raise ProfileConfigError("Database default_profile is required when multiple profiles are configured")
    selected_name = str(selected_name).strip()
    if selected_name not in profiles:
        raise ProfileConfigError(f"Database profile not found: {selected_name}")

    raw_config = profiles[selected_name]
    if not isinstance(raw_config, dict):
        raise ProfileConfigError(f"Database profile must be a mapping: {selected_name}")

    config = dict(raw_config)
    db_type = str(config.get("type") or "").strip().lower()
    if db_type == "postgres":
        db_type = "postgresql"
    if db_type not in SUPPORTED_TYPES:
        raise ProfileConfigError(f"Unsupported database type for profile {selected_name}: {db_type or '<missing>'}")
    config["type"] = db_type

    if db_type == "sqlite":
        sqlite_path = config.get("path") or config.get("database")
        if not sqlite_path:
            raise ProfileConfigError(f"SQLite profile requires 'path': {selected_name}")
        if str(sqlite_path) == ":memory:":
            resolved_path = ":memory:"
        else:
            path = Path(str(sqlite_path))
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            resolved_path = str(path)
        config["path"] = resolved_path
        config["database"] = resolved_path
        return DatabaseProfile(name=selected_name, type=db_type, config=config)

    missing = [key for key in ("host", "port", "database", "username", "password") if not config.get(key)]
    if missing:
        raise ProfileConfigError(f"Profile {selected_name} is missing required fields: {', '.join(missing)}")
    config.setdefault("schema", "public")
    config["port"] = int(config["port"])
    return DatabaseProfile(name=selected_name, type=db_type, config=config)


def get_active_profile() -> DatabaseProfile:
    return resolve_profile()
