"""SQLite lineage lookup and deterministic downstream traversal."""

from __future__ import annotations

import sqlite3
from collections import deque
from pathlib import Path

from .identifiers import compact_identifier, normalize_token, parse_input_table_name

LEGACY_ROOT_DIR = Path(__file__).resolve().parents[1] / "svn_check"
MAPPING_DB_PATH = LEGACY_ROOT_DIR / "runtime" / "sqlite" / "mapping_lineage.db"


def find_start_nodes_in_sqlite(
    table_name: str,
    column_name: str,
    db_path: str | Path = MAPPING_DB_PATH,
) -> list[tuple[str, str, str]]:
    schema, table = parse_input_table_name(table_name)
    column = normalize_token(column_name)
    query = """
        SELECT DISTINCT source_schema, source_table, source_column
        FROM lineage_edge
        WHERE source_table = ? AND source_column = ?
    """
    params: list[str] = [table, column]
    if schema:
        query += " AND source_schema = ?"
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
