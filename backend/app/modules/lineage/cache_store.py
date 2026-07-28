from __future__ import annotations

from contextlib import closing
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_db_parent(db_path: str | Path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def load_mapping_meta(db_path: str | Path, *, sqlite3_module) -> dict[str, str]:
    db_path = Path(db_path)
    if not db_path.exists():
        logger.warning("lineage mapping cache unavailable: %s", db_path)
        return {}
    with closing(sqlite3_module.connect(db_path)) as conn:
        rows = conn.execute("SELECT key, value FROM lineage_meta").fetchall()
    return {key: value for key, value in rows}


def get_mapping_db_status(db_path: str | Path, xlsx_path: str | Path, *, load_mapping_meta_func) -> dict:
    db_path, xlsx_path = Path(db_path), Path(xlsx_path)
    meta = load_mapping_meta_func(db_path)
    db_exists, xlsx_exists = db_path.exists(), xlsx_path.exists()
    is_fresh = False
    if db_exists and xlsx_exists and meta:
        xlsx_stat = xlsx_path.stat()
        is_fresh = meta.get("source_xlsx_mtime_ns") == str(xlsx_stat.st_mtime_ns) and meta.get("source_xlsx_size") == str(xlsx_stat.st_size)
    return {"db_exists": db_exists, "xlsx_exists": xlsx_exists, "is_fresh": is_fresh, "db_path": str(db_path), "xlsx_path": str(xlsx_path), "meta": meta}


def recreate_mapping_sqlite(xlsx_path: str | Path, db_path: str | Path, *, ensure_db_parent_func, load_lineage_edges_from_xlsx_func, normalize_identifier, normalize_token, sqlite3_module) -> dict:
    xlsx_path, db_path = Path(xlsx_path), Path(db_path)
    if not xlsx_path.is_file():
        logger.error("lineage mapping Excel unavailable: %s", xlsx_path)
        raise FileNotFoundError(f"Lineage mapping Excel does not exist: {xlsx_path}")
    ensure_db_parent_func(db_path)
    rows = load_lineage_edges_from_xlsx_func(xlsx_path)
    with closing(sqlite3_module.connect(db_path)) as conn, conn:
        conn.execute("DROP TABLE IF EXISTS lineage_edge")
        conn.execute("DROP TABLE IF EXISTS lineage_meta")
        conn.execute("""
            CREATE TABLE lineage_edge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_system TEXT NOT NULL, source_schema TEXT NOT NULL,
                source_table TEXT NOT NULL, source_column TEXT NOT NULL,
                target_system TEXT NOT NULL, target_schema TEXT NOT NULL,
                target_table TEXT NOT NULL, target_column TEXT NOT NULL
            )
        """)
        conn.execute("CREATE TABLE lineage_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        insert_rows = []
        for row in rows:
            source_schema, source_table, source_column = normalize_identifier(row["source_schema"], row["source_table"], row["source_column"])
            target_schema, target_table, target_column = normalize_identifier(row["target_schema"], row["target_table"], row["target_column"])
            insert_rows.append((normalize_token(row["source_system"]), source_schema, source_table, source_column, normalize_token(row["target_system"]), target_schema, target_table, target_column))
        conn.executemany("""
            INSERT INTO lineage_edge (
                source_system, source_schema, source_table, source_column,
                target_system, target_schema, target_table, target_column
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_rows)
        conn.execute("CREATE INDEX idx_lineage_source ON lineage_edge(source_schema, source_table, source_column)")
        conn.execute("CREATE INDEX idx_lineage_target ON lineage_edge(target_schema, target_table, target_column)")
        xlsx_stat = xlsx_path.stat()
        meta_items = {
            "source_xlsx_path": str(xlsx_path), "source_xlsx_mtime_ns": str(xlsx_stat.st_mtime_ns),
            "source_xlsx_size": str(xlsx_stat.st_size), "imported_at": datetime.now().isoformat(timespec="seconds"),
            "edge_count": str(len(insert_rows)),
        }
        conn.executemany("INSERT INTO lineage_meta(key, value) VALUES(?, ?)", list(meta_items.items()))
        conn.commit()
    return {"db_path": str(db_path), "xlsx_path": str(xlsx_path), "edge_count": len(rows)}
