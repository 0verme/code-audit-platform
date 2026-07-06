from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = BACKEND_DIR / "configs" / "database.yaml"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "data" / "app.db"

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


def _default_config() -> dict[str, Any]:
    return {
        "default_profile": "sqlite",
        "profiles": {
            "sqlite": {
                "type": "sqlite",
                "path": str(DEFAULT_SQLITE_PATH),
            }
        },
    }


def load_database_config(config_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    path = resolve_config_path(config_path)
    explicit_path = bool(config_path or os.getenv(CONFIG_PATH_ENV))
    if not path.exists():
        if explicit_path:
            raise ProfileConfigError(f"Database config file does not exist: {path}")
        return _default_config()

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ProfileConfigError(f"Invalid database config YAML: {path}") from exc
    except OSError as exc:
        raise ProfileConfigError(f"Unable to read database config file: {path}") from exc

    if not isinstance(data, dict):
        raise ProfileConfigError(f"Database config must be a mapping: {path}")

    data.setdefault("default_profile", "sqlite")
    data.setdefault("profiles", {})
    if not isinstance(data["profiles"], dict):
        raise ProfileConfigError("Database config 'profiles' must be a mapping")
    return data


def resolve_profile(
    profile_name: str | None = None,
    *,
    config_path: str | os.PathLike[str] | None = None,
) -> DatabaseProfile:
    data = load_database_config(config_path)
    selected_name = (profile_name or os.getenv(PROFILE_ENV) or data.get("default_profile") or "sqlite").strip()
    profiles = data["profiles"]
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
