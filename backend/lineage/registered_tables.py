from __future__ import annotations

from .identifiers import normalize_registered_table_name, normalize_value


def load_registered_result_tables(profile: str = 'czcb', select_sql_with_profile=None) -> set[str]:
    if select_sql_with_profile is None:
        from db.metadata.compat.router import select_sql_with_profile as default_select_sql_with_profile

        select_sql_with_profile = default_select_sql_with_profile
    sql = """
        SELECT substr(p.k,5) AS table_name
        FROM dwp.p_job_hjj j
        INNER JOIN dwp.p_program_hjj p
        ON j.e = p.b
        WHERE substr(p.k,5) IS NOT NULL
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
    profile: str = 'czcb',
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
