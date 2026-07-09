from __future__ import annotations

from pathlib import Path

from .connection import _resolve_profile as resolve_runtime_profile
from .connection import get_connection, split_sql_statements
from .profiles import DatabaseProfile
from .tables import RUNTIME_TABLES, render_table_tokens

SQL_DIR = Path(__file__).resolve().parent / "sql"
SCHEMA_FILES = {
    "sqlite": SQL_DIR / "sqlite" / "schema.sql",
    "postgresql": SQL_DIR / "postgresql" / "schema.sql",
    "dws": SQL_DIR / "dws" / "schema.sql",
}
MIGRATION_FILES = {
    "postgresql": SQL_DIR / "postgresql" / "migrate_runtime_tables.sql",
}


def _resolve_profile(profile: str | DatabaseProfile | None = None) -> DatabaseProfile:
    return resolve_runtime_profile(profile)


def schema_path_for(profile: str | DatabaseProfile | None = None) -> Path:
    return SCHEMA_FILES[_resolve_profile(profile).type]


def migration_path_for(profile: str | DatabaseProfile | None = None) -> Path | None:
    return MIGRATION_FILES.get(_resolve_profile(profile).type)


def load_schema_sql(profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    return render_table_tokens(schema_path_for(resolved).read_text(encoding="utf-8"), resolved)


def load_runtime_migration_sql(profile: str | DatabaseProfile | None = None) -> str:
    resolved = _resolve_profile(profile)
    path = migration_path_for(resolved)
    if path is None or not path.exists():
        return ""
    return render_table_tokens(path.read_text(encoding="utf-8"), resolved)


def schema_statements(profile: str | DatabaseProfile | None = None) -> list[str]:
    return split_sql_statements(load_schema_sql(profile))


def runtime_migration_statements(profile: str | DatabaseProfile | None = None) -> list[str]:
    sql_text = load_runtime_migration_sql(profile)
    if not sql_text:
        return []
    return split_sql_statements(sql_text)


def initialize_schema(profile: str | DatabaseProfile | None = None, *, runner=None) -> None:
    resolved = _resolve_profile(profile)
    if runner is not None:
        for statement in schema_statements(resolved):
            runner.execute(statement)
        return
    with get_connection(resolved) as connection:
        connection.executescript(load_schema_sql(resolved))

def ensure_runtime_tables(profile: str | DatabaseProfile | None = None, *, runner=None) -> None:
    resolved = _resolve_profile(profile)
    if runner is not None:
        for statement in runtime_migration_statements(resolved):
            runner.execute(statement)
        for statement in schema_statements(resolved):
            runner.execute(statement)
        return
    migration_sql = load_runtime_migration_sql(resolved)
    with get_connection(resolved) as connection:
        if migration_sql:
            connection.executescript(migration_sql)
        connection.executescript(load_schema_sql(resolved))

def init_db(profile: str | DatabaseProfile | None = None, *, runner=None) -> None:
    ensure_runtime_tables(profile, runner=runner)
