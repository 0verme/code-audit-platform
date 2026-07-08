from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db.schema import RUNTIME_TABLES  # noqa: E402
from db.sql_runner import SQLRunner  # noqa: E402


PRIMARY_KEYS = {
    "projects": "id",
    "audit_tasks": "id",
    "task_reports": "task_id",
    "audit_results": "id",
    "fine_report_items": "id",
}


@dataclass
class TableMigrationResult:
    table: str
    source_count: int
    target_before: int
    inserted: int
    skipped: int
    target_after: int


class SQLiteToProfileMigrator:
    def __init__(self, source: str | Path, target_profile: str, *, runner: SQLRunner | None = None, dry_run: bool = False):
        self.source = Path(source)
        self.target_profile = target_profile
        self.runner = runner or SQLRunner(target_profile)
        self.dry_run = dry_run

    def migrate(self) -> list[TableMigrationResult]:
        if not self.source.exists():
            raise FileNotFoundError(f"Source SQLite database does not exist: {self.source}")

        results: list[TableMigrationResult] = []
        with sqlite3.connect(self.source) as source_connection:
            source_connection.row_factory = sqlite3.Row
            for table in RUNTIME_TABLES:
                results.append(self._migrate_table(source_connection, table))
        return results

    def _migrate_table(self, source_connection: sqlite3.Connection, table: str) -> TableMigrationResult:
        source_rows = [dict(row) for row in source_connection.execute(f"SELECT * FROM {table} ORDER BY {PRIMARY_KEYS[table]}").fetchall()]
        source_count = len(source_rows)
        target_before = self._target_count(table)
        inserted = 0
        skipped = 0

        for row in source_rows:
            pk_name = PRIMARY_KEYS[table]
            pk_value = row[pk_name]
            if self._target_exists(table, pk_name, pk_value):
                skipped += 1
                continue
            if not self.dry_run:
                self._insert_row(table, row)
            inserted += 1

        target_after = target_before if self.dry_run else self._target_count(table)
        if not self.dry_run and target_after != target_before + inserted:
            raise RuntimeError(
                f"Row count validation failed for {table}: before={target_before}, inserted={inserted}, after={target_after}"
            )
        return TableMigrationResult(table, source_count, target_before, inserted, skipped, target_after)

    def _target_count(self, table: str) -> int:
        row = self.runner.query_one("SELECT COUNT(*) AS count FROM " + "{{table:" + table + "}}")
        return int(row["count"] if row else 0)

    def _target_exists(self, table: str, pk_name: str, pk_value: Any) -> bool:
        row = self.runner.query_one(
            f"SELECT {pk_name} FROM " + "{{table:" + table + "}}" + f" WHERE {pk_name} = ?",
            (pk_value,),
        )
        return row is not None

    def _insert_row(self, table: str, row: dict[str, Any]) -> None:
        columns = list(row.keys())
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)
        sql = "INSERT INTO " + "{{table:" + table + "}}" + f" ({column_sql}) VALUES ({placeholders})"
        self.runner.execute(sql, tuple(row[column] for column in columns))


def print_results(results: list[TableMigrationResult], *, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"SQLite profile migration {mode}")
    for result in results:
        print(
            f"{result.table}: source={result.source_count}, target_before={result.target_before}, "
            f"inserted={result.inserted}, skipped={result.skipped}, target_after={result.target_after}"
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Migrate platform runtime tables from SQLite to a target DB profile.")
    parser.add_argument("--source", default=str(BACKEND_DIR / "data" / "app.db"), help="Source SQLite database file.")
    parser.add_argument("--target-profile", required=True, help="Target database profile name.")
    parser.add_argument("--dry-run", action="store_true", help="Report migration actions without writing target rows.")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    migrator = SQLiteToProfileMigrator(args.source, args.target_profile, dry_run=args.dry_run)
    results = migrator.migrate()
    print_results(results, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
