from __future__ import annotations

from .identifiers import normalize_registered_table_name, normalize_value
from app.db.profiles import get_active_profile
from app.modules.metadata.services.metadata_model import column_name, table_name as metadata_table_name


def load_registered_result_tables(profile: str | None = None, select_sql_with_profile=None) -> set[str]:
    if select_sql_with_profile is None:
        from app.db.metadata.compat.router import select_sql_with_profile as default_select_sql_with_profile

        select_sql_with_profile = default_select_sql_with_profile
    profile = profile or get_active_profile().name
    sql = f"""
        SELECT DISTINCT substr(p.{column_name('programs', 'result_table', profile)},5) AS table_name
        FROM {metadata_table_name('jobs', profile)} j
        INNER JOIN {metadata_table_name('programs', profile)} p
        ON j.{column_name('jobs', 'program_key', profile)} = p.{column_name('programs', 'program_key', profile)}
        WHERE p.{column_name('programs', 'result_table', profile)} IS NOT NULL
    """
    rows = select_sql_with_profile(profile, sql) or []
    result_tables = set()
    for row in rows:
        table_name = normalize_value(row[0]) if row else ''
        normalized_table_name = normalize_registered_table_name(table_name)
        if normalized_table_name:
            result_tables.add(normalized_table_name)
    return result_tables


def filter_registered_result_nodes(
    nodes: list[tuple[str, str, str]],
    result_tables: set[str] | None = None,
    profile: str | None = None,
    load_registered_result_tables_func=None,
) -> list[tuple[str, str, str]]:
    if load_registered_result_tables_func is None:
        load_registered_result_tables_func = load_registered_result_tables
    result_tables = result_tables if result_tables is not None else load_registered_result_tables_func(profile)
    filtered_nodes = []
    for schema, table, column in nodes:
        full_name = normalize_registered_table_name(f'{schema}.{table}' if schema else table)
        if full_name in result_tables:
            filtered_nodes.append((schema, table, column))
    return filtered_nodes
