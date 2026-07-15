from __future__ import annotations


def normalize_value(value) -> str:
    if value is None:
        return ''
    return str(value).strip().replace('\n', '').replace('\r', '')


def normalize_token(value) -> str:
    return normalize_value(value).upper().replace(' ', '')


def parse_input_table_name(table_name: str) -> tuple[str, str]:
    normalized = normalize_token(table_name)
    if '.' in normalized:
        schema, table = normalized.split('.', 1)
        return schema, table
    return '', normalized


def normalize_identifier(schema: str, table: str, column: str) -> tuple[str, str, str]:
    normalized_schema = normalize_token(schema)
    normalized_table = normalize_token(table)
    if not normalized_schema and '.' in normalized_table:
        normalized_schema, normalized_table = normalized_table.split('.', 1)
    return normalized_schema, normalized_table, normalize_token(column)


def compact_identifier(identifier: tuple[str, str, str]) -> str:
    schema, table, column = identifier
    table_name = f'{schema}.{table}' if schema else table
    return f'{table_name}.{column}'


def normalize_registered_table_name(table_name: str) -> str:
    clean_name = normalize_value(table_name).split(' ')[0]
    return normalize_token(clean_name)
