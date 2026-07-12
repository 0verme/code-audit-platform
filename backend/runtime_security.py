"""Small, testable runtime security defaults for the HTTP audit service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def parse_bool(value: str | None, *, default: bool, name: str) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value for {name}")


def _parse_list(value: str | None, *, name: str, separator: str) -> tuple[str, ...]:
    if not value or not value.strip():
        return ()
    text = value.strip()
    if text.startswith("["):
        try:
            entries = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON list for {name}") from exc
        if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
            raise ValueError(f"{name} must be a JSON array of strings")
    else:
        entries = text.split(separator)
    return tuple(item.strip() for item in entries if item.strip())


@dataclass(frozen=True)
class RuntimeSecuritySettings:
    local_source_enabled: bool = False
    local_source_roots: tuple[str, ...] = ()
    cors_origins: tuple[str, ...] = ()
    host: str = "127.0.0.1"
    port: int = 5088
    debug: bool = False


def get_runtime_security_settings(environ: dict[str, str] | None = None) -> RuntimeSecuritySettings:
    env = os.environ if environ is None else environ
    local_source_enabled = parse_bool(env.get("AUDIT_LOCAL_SOURCE_ENABLED"), default=False, name="AUDIT_LOCAL_SOURCE_ENABLED")
    debug = parse_bool(env.get("AUDIT_DEBUG"), default=False, name="AUDIT_DEBUG")
    roots = _parse_list(env.get("AUDIT_LOCAL_SOURCE_ROOTS"), name="AUDIT_LOCAL_SOURCE_ROOTS", separator=os.pathsep)
    origins = _parse_list(env.get("AUDIT_CORS_ORIGINS"), name="AUDIT_CORS_ORIGINS", separator=",")
    if not origins:
        origins = DEFAULT_CORS_ORIGINS
    if "*" in origins:
        raise ValueError("AUDIT_CORS_ORIGINS must not contain '*'")
    try:
        port = int(env.get("AUDIT_PORT", "5088"))
    except ValueError as exc:
        raise ValueError("AUDIT_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("AUDIT_PORT must be between 1 and 65535")
    return RuntimeSecuritySettings(
        local_source_enabled=local_source_enabled,
        local_source_roots=roots,
        cors_origins=origins,
        host=env.get("AUDIT_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=port,
        debug=debug,
    )


def resolve_local_roots(settings: RuntimeSecuritySettings) -> tuple[Path, ...]:
    roots = []
    for root in settings.local_source_roots:
        candidate = Path(root).expanduser()
        if not candidate.is_dir():
            raise ValueError("Configured local workspace root does not exist or is not a directory")
        roots.append(candidate.resolve())
    return tuple(roots)
