"""Stable, overridable locations for optional lineage mapping resources."""

from __future__ import annotations

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
LINEAGE_DATA_DIR = BACKEND_DIR / "data" / "lineage"
MAPPING_XLSX_PATH = LINEAGE_DATA_DIR / "mapping.xlsx"
MAPPING_DB_PATH = LINEAGE_DATA_DIR / "mapping_lineage.db"


def _resolve_path_override(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    candidate = Path(value).expanduser()
    return candidate if candidate.is_absolute() else BACKEND_DIR / candidate


def resolve_mapping_xlsx_path() -> Path:
    return _resolve_path_override("LINEAGE_MAPPING_EXCEL_PATH", MAPPING_XLSX_PATH)


def resolve_mapping_db_path() -> Path:
    return _resolve_path_override("LINEAGE_MAPPING_DB_PATH", MAPPING_DB_PATH)
