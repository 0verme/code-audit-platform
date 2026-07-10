# -*- coding: utf-8 -*-
"""Lineage compatibility module with mixed short-term responsibilities.

Current responsibilities intentionally remain co-located:
- online metadata query
- SQLite cache build
- Excel import
- lineage traversal

This module is still part of the active compatibility path and is documented
before any future split work. This round does not change behavior.
"""

from __future__ import annotations

import sqlite3
from collections import deque
from pathlib import Path

from shared.db.router import select_sql_with_profile
from shared.lineage import cache_store as cache_store_helpers
from shared.lineage.identifiers import (
    compact_identifier,
    normalize_identifier,
    normalize_registered_table_name,
    normalize_token,
    normalize_value,
    parse_input_table_name,
)
from shared.lineage import registered_tables as registered_tables_helpers
from shared.lineage import xlsx_loader as xlsx_loader_helpers

ROOT_DIR = Path(__file__).resolve().parents[2]
MAPPING_XLSX_PATH = ROOT_DIR / 'resources' / 'xlsx' / 'mapping.xlsx'
MAPPING_DB_PATH = ROOT_DIR / 'runtime' / 'sqlite' / 'mapping_lineage.db'

HEADER_ALIASES = {
    'target_system': {'鐩爣绯荤粺'},
    'target_schema': {'鐩爣妯″紡'},
    'target_table': {'鐩爣琛?'},
    'target_column': {'鐩爣瀛楁'},
    'source_system': {'婧愮郴缁?'},
    'source_schema': {'婧愭ā寮?'},
    'source_table': {'婧愯〃'},
    'source_column': {'婧愬瓧娈?'},
}


def detect_header_row(ws) -> tuple[int, dict[str, int]]:
    return xlsx_loader_helpers.detect_header_row(
        ws,
        header_aliases=HEADER_ALIASES,
        normalize_value=normalize_value,
    )


def load_lineage_edges_from_xlsx(xlsx_path: str | Path = MAPPING_XLSX_PATH) -> list[dict]:
    return xlsx_loader_helpers.load_lineage_edges_from_xlsx(
        xlsx_path,
        detect_header_row_func=detect_header_row,
        normalize_value=normalize_value,
    )


def ensure_db_parent(db_path: str | Path = MAPPING_DB_PATH):
    cache_store_helpers.ensure_db_parent(db_path)


def recreate_mapping_sqlite(xlsx_path: str | Path = MAPPING_XLSX_PATH, db_path: str | Path = MAPPING_DB_PATH) -> dict:
    return cache_store_helpers.recreate_mapping_sqlite(
        xlsx_path,
        db_path,
        ensure_db_parent_func=ensure_db_parent,
        load_lineage_edges_from_xlsx_func=load_lineage_edges_from_xlsx,
        normalize_identifier=normalize_identifier,
        normalize_token=normalize_token,
        sqlite3_module=sqlite3,
    )


def load_mapping_meta(db_path: str | Path = MAPPING_DB_PATH) -> dict[str, str]:
    return cache_store_helpers.load_mapping_meta(
        db_path,
        sqlite3_module=sqlite3,
    )


def get_mapping_db_status(db_path: str | Path = MAPPING_DB_PATH, xlsx_path: str | Path = MAPPING_XLSX_PATH) -> dict:
    return cache_store_helpers.get_mapping_db_status(
        db_path,
        xlsx_path,
        load_mapping_meta_func=load_mapping_meta,
    )


def load_registered_result_tables(profile: str = 'czcb') -> set[str]:
    return registered_tables_helpers.load_registered_result_tables(
        profile=profile,
        select_sql_with_profile=select_sql_with_profile,
    )


def filter_registered_result_nodes(
    nodes: list[tuple[str, str, str]],
    result_tables: set[str] | None = None,
    profile: str = 'czcb',
) -> list[tuple[str, str, str]]:
    return registered_tables_helpers.filter_registered_result_nodes(
        nodes=nodes,
        result_tables=result_tables,
        profile=profile,
        load_registered_result_tables_func=load_registered_result_tables,
    )


def find_start_nodes_in_sqlite(table_name: str, column_name: str, db_path: str | Path = MAPPING_DB_PATH) -> list[tuple[str, str, str]]:
    schema, table = parse_input_table_name(table_name)
    column = normalize_token(column_name)
    query = """
        SELECT DISTINCT source_schema, source_table, source_column
        FROM lineage_edge
        WHERE source_table = ? AND source_column = ?
    """
    params: list[str] = [table, column]
    if schema:
        query += ' AND source_schema = ?'
        params.append(schema)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def walk_downstream_in_sqlite(
    start_nodes: list[tuple[str, str, str]],
    db_path: str | Path = MAPPING_DB_PATH,
    max_depth: int | None = None,
) -> tuple[list[list[str]], list[tuple[str, str, str]]]:
    queue = deque()
    visited = set()
    downstream_nodes = set()
    relation_rows = []

    with sqlite3.connect(db_path) as conn:
        for start in start_nodes:
            queue.append((start, 0))
            visited.add(start)

        while queue:
            current, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue
            source_schema, source_table, source_column = current
            rows = conn.execute(
                """
                SELECT DISTINCT target_schema, target_table, target_column
                FROM lineage_edge
                WHERE source_schema = ? AND source_table = ? AND source_column = ?
                """,
                [source_schema, source_table, source_column],
            ).fetchall()
            for row in rows:
                target = (row[0], row[1], row[2])
                relation_rows.append([depth + 1, compact_identifier(current), compact_identifier(target)])
                downstream_nodes.add(target)
                if target not in visited:
                    visited.add(target)
                    queue.append((target, depth + 1))

    relation_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    ordered_nodes = sorted(downstream_nodes)
    return relation_rows, ordered_nodes
