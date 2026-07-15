"""SQLite lineage lookup and deterministic downstream traversal."""

from __future__ import annotations

import logging
import sqlite3
from collections import deque
from pathlib import Path

from .identifiers import compact_identifier, normalize_token, parse_input_table_name
from .paths import MAPPING_DB_PATH

logger = logging.getLogger(__name__)


def _require_mapping_db(db_path: str | Path) -> Path:
    path = Path(db_path)
    if not path.is_file():
        logger.error("lineage mapping cache unavailable: %s", path)
        raise FileNotFoundError(f"Lineage mapping SQLite cache does not exist: {path}")
    return path


def find_start_nodes_in_sqlite(table_name: str, column_name: str, db_path: str | Path = MAPPING_DB_PATH) -> list[tuple[str, str, str]]:
    schema, table = parse_input_table_name(table_name)
    column = normalize_token(column_name)
    query = "SELECT DISTINCT source_schema, source_table, source_column FROM lineage_edge WHERE source_table = ? AND source_column = ?"
    params: list[str] = [table, column]
    if schema:
        query += " AND source_schema = ?"
        params.append(schema)
    with sqlite3.connect(_require_mapping_db(db_path)) as conn:
        rows = conn.execute(query, params).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def walk_downstream_in_sqlite(start_nodes, db_path: str | Path = MAPPING_DB_PATH, max_depth: int | None = None):
    queue, visited, downstream_nodes, relation_rows = deque(), set(), set(), []
    with sqlite3.connect(_require_mapping_db(db_path)) as conn:
        for start in start_nodes:
            queue.append((start, 0))
            visited.add(start)
        while queue:
            current, depth = queue.popleft()
            if max_depth is not None and depth >= max_depth:
                continue
            rows = conn.execute(
                "SELECT DISTINCT target_schema, target_table, target_column FROM lineage_edge WHERE source_schema = ? AND source_table = ? AND source_column = ?",
                list(current),
            ).fetchall()
            for row in rows:
                target = (row[0], row[1], row[2])
                relation_rows.append([depth + 1, compact_identifier(current), compact_identifier(target)])
                downstream_nodes.add(target)
                if target not in visited:
                    visited.add(target)
                    queue.append((target, depth + 1))
    relation_rows.sort(key=lambda item: (item[0], item[1], item[2]))
    return relation_rows, sorted(downstream_nodes)
