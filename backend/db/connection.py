from __future__ import annotations

from typing import Any

from .errors import DatabaseDriverError
from .profiles import DatabaseProfile, resolve_profile
from .tables import DEFAULT_RUNTIME_SCHEMA

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


def _resolve_profile(profile: str | DatabaseProfile | None = None) -> DatabaseProfile:
    if isinstance(profile, DatabaseProfile):
        return profile
    return resolve_profile(profile)


def connect(profile: str | DatabaseProfile | None = None) -> Any:
    resolved = _resolve_profile(profile)
    if resolved.type in {"postgresql", "dws"}:
        return connect_postgresql(resolved)
    raise DatabaseDriverError(f"Unsupported database type: {resolved.type}")


def connect_postgresql(profile: DatabaseProfile) -> Any:
    config = profile.config
    options = _build_pg_options(config)
    if psycopg is not None:
        return psycopg.connect(
            host=config["host"],
            port=int(config["port"]),
            dbname=config["database"],
            user=config["username"],
            password=config["password"],
            connect_timeout=int(config.get("connect_timeout", 30)),
            autocommit=False,
            options=options,
        )
    if psycopg2 is not None:
        connection = psycopg2.connect(
            host=config["host"],
            port=int(config["port"]),
            dbname=config["database"],
            user=config["username"],
            password=config["password"],
            connect_timeout=int(config.get("connect_timeout", 30)),
            options=options,
        )
        connection.autocommit = False
        return connection
    raise DatabaseDriverError("PostgreSQL/DWS driver not installed. Install psycopg[binary] or psycopg2-binary.")


def _build_pg_options(config: dict[str, Any]) -> str | None:
    options: list[str] = []
    schema = str(config.get("schema") or DEFAULT_RUNTIME_SCHEMA).strip()
    if schema:
        options.append(f"-c search_path={schema}")
    statement_timeout_ms = config.get("statement_timeout_ms")
    if statement_timeout_ms is not None:
        options.append(f"-c statement_timeout={int(statement_timeout_ms)}")
    return " ".join(options) or None
