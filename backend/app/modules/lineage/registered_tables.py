from __future__ import annotations

from dataclasses import dataclass

from .identifiers import normalize_registered_table_name, normalize_value
from app.db.profiles import get_metadata_profile
from app.modules.metadata.services.metadata_model import column_name, table_name as metadata_table_name


@dataclass(frozen=True)
class ResultTableCatalogSnapshot:
    registered: frozenset[str]
    disabled: frozenset[str]


def load_result_table_catalog_snapshot(profile: str | None = None, select_sql_with_profile=None) -> ResultTableCatalogSnapshot:
    if select_sql_with_profile is None:
        from app.db.metadata.compat.router import select_sql_with_profile as default_select_sql_with_profile

        select_sql_with_profile = default_select_sql_with_profile
    profile = profile or get_metadata_profile().name
    sql = f"""
        SELECT DISTINCT substr(p.{column_name('programs', 'result_table', profile)},5) AS table_name,
               MAX(CASE WHEN CAST(j.{column_name('jobs', 'status', profile)} AS VARCHAR(32)) = '9' THEN 1 ELSE 0 END) AS disabled
        FROM {metadata_table_name('jobs', profile)} j
        INNER JOIN {metadata_table_name('programs', profile)} p
        ON j.{column_name('jobs', 'program_key', profile)} = p.{column_name('programs', 'program_key', profile)}
        WHERE p.{column_name('programs', 'result_table', profile)} IS NOT NULL
          AND substr(p.{column_name('programs', 'result_table', profile)},5) IS NOT NULL
        GROUP BY substr(p.{column_name('programs', 'result_table', profile)},5)
    """
    rows = select_sql_with_profile(profile, sql) or []
    registered = set()
    disabled = set()
    for row in rows:
        table_name = normalize_value(row[0]) if row else ''
        normalized_table_name = normalize_registered_table_name(table_name)
        if normalized_table_name:
            registered.add(normalized_table_name)
            if len(row) > 1 and str(row[1] or '').strip().lower() not in ('', '0', 'false', 'n', 'no'):
                disabled.add(normalized_table_name)
    return ResultTableCatalogSnapshot(frozenset(registered), frozenset(disabled))


def load_registered_result_tables(profile: str | None = None, select_sql_with_profile=None) -> set[str]:
    return set(load_result_table_catalog_snapshot(profile, select_sql_with_profile).registered)


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
