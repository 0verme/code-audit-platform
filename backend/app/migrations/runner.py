from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from app.db.connection import split_sql_statements
from app.db.profiles import DatabaseProfile
from app.db.tables import render_table_tokens
from .errors import VerificationError
from .manifest import Migration, load_manifest


@dataclass(frozen=True)
class MigrationState:
    applied: dict[str, tuple[str, str]]
    pending: list[Migration]


class MigrationRunner:
    """Versioned, repeatable migrations that are never run implicitly at app startup."""

    def __init__(self, connection, dialect: str, root: Path, profile: DatabaseProfile | None = None):
        if dialect not in {"sqlite", "postgresql", "dws"}:
            raise VerificationError(f"Unsupported database dialect: {dialect}")
        self.connection = connection
        self.dialect = dialect
        self.root = Path(root)
        self.profile = profile or DatabaseProfile("migration", dialect, {"type": dialect, "table_prefix": ""})
        self.migrations = load_manifest(self.root)

    @property
    def placeholder(self) -> str:
        return "?" if self.dialect in {"sqlite", "dws"} else "%s"

    def _execute(self, sql: str, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor

    def ensure_ledger(self) -> None:
        self._execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(64) PRIMARY KEY, name VARCHAR(255) NOT NULL,
            checksum VARCHAR(64) NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            execution_ms INTEGER NOT NULL
        )""").close()
        self.connection.commit()

    def status(self, *, create_ledger: bool = False) -> MigrationState:
        if create_ledger:
            self.ensure_ledger()
        try:
            cursor = self._execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version")
            rows = cursor.fetchall()
            cursor.close()
        except Exception as exc:
            raise VerificationError("Migration ledger is not installed; run migration apply") from exc
        applied = {str(row[0]): (str(row[1]), str(row[2])) for row in rows}
        known = {migration.version: migration for migration in self.migrations}
        unknown = sorted(set(applied) - set(known))
        changed = [version for version, (_, checksum) in applied.items() if version in known and checksum != known[version].checksum(self.dialect)]
        if unknown or changed:
            details = []
            if unknown:
                details.append("unknown versions: " + ", ".join(unknown))
            if changed:
                details.append("checksum mismatch: " + ", ".join(changed))
            raise VerificationError("; ".join(details))
        return MigrationState(applied, [migration for migration in self.migrations if migration.version not in applied])

    def apply(self) -> list[str]:
        self.ensure_ledger()
        state = self.status()
        executed = []
        try:
            for migration in state.pending:
                started = time.monotonic()
                sql = render_table_tokens(migration.files[self.dialect].read_text(encoding="utf-8"), self.profile)
                for statement in split_sql_statements(sql):
                    self._execute(statement).close()
                elapsed = int((time.monotonic() - started) * 1000)
                self._execute(
                    f"INSERT INTO schema_migrations (version, name, checksum, execution_ms) VALUES ({self.placeholder}, {self.placeholder}, {self.placeholder}, {self.placeholder})",
                    (migration.version, migration.name, migration.checksum(self.dialect), elapsed),
                ).close()
                self.connection.commit()
                executed.append(migration.version)
            return executed
        except Exception:
            self.connection.rollback()
            raise
