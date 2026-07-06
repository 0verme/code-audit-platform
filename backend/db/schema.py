from __future__ import annotations

from pathlib import Path

from .profiles import DatabaseProfile, resolve_profile
from .sql_runner import SQLRunner


RUNTIME_TABLES = (
    "projects",
    "audit_tasks",
    "task_reports",
    "audit_results",
    "fine_report_items",
)

SCHEMA_DIR = Path(__file__).resolve().parent
SCHEMA_FILES = {
    "sqlite": SCHEMA_DIR / "schema_sqlite.sql",
    "postgresql": SCHEMA_DIR / "schema_pg.sql",
    "dws": SCHEMA_DIR / "schema_dws.sql",
}


def schema_path_for(profile: str | DatabaseProfile | None = None) -> Path:
    resolved = profile if isinstance(profile, DatabaseProfile) else resolve_profile(profile)
    return SCHEMA_FILES[resolved.type]


def load_schema_sql(profile: str | DatabaseProfile | None = None) -> str:
    path = schema_path_for(profile)
    return path.read_text(encoding="utf-8")


def schema_statements(profile: str | DatabaseProfile | None = None) -> list[str]:
    sql_text = load_schema_sql(profile)
    return [statement.strip() for statement in sql_text.split(";") if statement.strip()]


def initialize_schema(
    profile: str | DatabaseProfile | None = None,
    *,
    runner: SQLRunner | None = None,
) -> None:
    resolved = profile if isinstance(profile, DatabaseProfile) else resolve_profile(profile)
    sql_runner = runner or SQLRunner(resolved)
    for statement in schema_statements(resolved):
        sql_runner.execute(statement)
