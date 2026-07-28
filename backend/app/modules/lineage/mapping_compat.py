# -*- coding: utf-8 -*-
"""Compatibility facade for lineage mapping import, cache, and traversal."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.db.metadata.compat.router import select_sql_with_profile
from app.db.profiles import get_metadata_profile
from . import cache_store as cache_store_helpers
from . import registered_tables as registered_tables_helpers
from . import traversal as traversal_helpers
from . import xlsx_loader as xlsx_loader_helpers
from .identifiers import (
    compact_identifier as compact_identifier,
    normalize_identifier,
    normalize_registered_table_name as normalize_registered_table_name,
    normalize_token,
    normalize_value,
    parse_input_table_name as parse_input_table_name,
)
from .paths import resolve_mapping_db_path, resolve_mapping_xlsx_path


HEADER_ALIASES = {
    "target_system": {"target_system", "目标系统", "下游系统"},
    "target_schema": {"target_schema", "目标模式", "目标库名", "下游库名"},
    "target_table": {"target_table", "目标表", "目标表名", "下游表", "下游表名", "结果表"},
    "target_column": {"target_column", "目标字段", "目标字段名", "下游字段", "下游字段名"},
    "source_system": {"source_system", "源系统", "来源系统", "上游系统"},
    "source_schema": {"source_schema", "源模式", "源库名", "来源库名", "上游库名"},
    "source_table": {"source_table", "源表", "源表名", "来源表", "上游表", "上游表名"},
    "source_column": {"source_column", "源字段", "源字段名", "来源字段", "上游字段", "上游字段名"},
}

# Compatibility name retained for callers/tests that patched the former runtime resolver.
get_active_profile = get_metadata_profile


def detect_header_row(ws) -> tuple[int, dict[str, int]]:
    return xlsx_loader_helpers.detect_header_row(ws, header_aliases=HEADER_ALIASES, normalize_value=normalize_value)


def load_lineage_edges_from_xlsx(xlsx_path: str | Path | None = None) -> list[dict]:
    return xlsx_loader_helpers.load_lineage_edges_from_xlsx(
        xlsx_path or resolve_mapping_xlsx_path(), detect_header_row_func=detect_header_row, normalize_value=normalize_value
    )


def ensure_db_parent(db_path: str | Path | None = None):
    cache_store_helpers.ensure_db_parent(db_path or resolve_mapping_db_path())


def recreate_mapping_sqlite(xlsx_path: str | Path | None = None, db_path: str | Path | None = None) -> dict:
    return cache_store_helpers.recreate_mapping_sqlite(
        xlsx_path or resolve_mapping_xlsx_path(), db_path or resolve_mapping_db_path(),
        ensure_db_parent_func=ensure_db_parent, load_lineage_edges_from_xlsx_func=load_lineage_edges_from_xlsx,
        normalize_identifier=normalize_identifier, normalize_token=normalize_token, sqlite3_module=sqlite3,
    )


def load_mapping_meta(db_path: str | Path | None = None) -> dict[str, str]:
    return cache_store_helpers.load_mapping_meta(db_path or resolve_mapping_db_path(), sqlite3_module=sqlite3)


def get_mapping_db_status(db_path: str | Path | None = None, xlsx_path: str | Path | None = None) -> dict:
    return cache_store_helpers.get_mapping_db_status(
        db_path or resolve_mapping_db_path(), xlsx_path or resolve_mapping_xlsx_path(), load_mapping_meta_func=load_mapping_meta
    )


def load_registered_result_tables(profile: str | None = None) -> set[str]:
    profile = profile or get_active_profile().name
    return registered_tables_helpers.load_registered_result_tables(profile=profile, select_sql_with_profile=select_sql_with_profile)


def load_result_table_catalog_snapshot(profile: str | None = None):
    profile = profile or get_active_profile().name
    return registered_tables_helpers.load_result_table_catalog_snapshot(
        profile=profile,
        select_sql_with_profile=select_sql_with_profile,
    )


def filter_registered_result_nodes(nodes, result_tables=None, profile: str | None = None):
    return registered_tables_helpers.filter_registered_result_nodes(
        nodes=nodes, result_tables=result_tables, profile=profile, load_registered_result_tables_func=load_registered_result_tables
    )


def find_start_nodes_in_sqlite(table_name: str, column_name: str, db_path: str | Path | None = None) -> list[tuple[str, str, str]]:
    return traversal_helpers.find_start_nodes_in_sqlite(table_name, column_name, db_path or resolve_mapping_db_path())


def walk_downstream_in_sqlite(start_nodes, db_path: str | Path | None = None, max_depth: int | None = None):
    return traversal_helpers.walk_downstream_in_sqlite(start_nodes, db_path or resolve_mapping_db_path(), max_depth)
