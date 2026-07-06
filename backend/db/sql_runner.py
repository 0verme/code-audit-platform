from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterable, Iterator, Sequence

from .connection import connect
from .errors import SqlExecutionError
from .profiles import DatabaseProfile, resolve_profile


Params = Sequence[Any] | None
ConnectionFactory = Callable[[DatabaseProfile], Any]


class SQLRunner:
    def __init__(
        self,
        profile: str | DatabaseProfile | None = None,
        *,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        self.profile = profile if isinstance(profile, DatabaseProfile) else resolve_profile(profile)
        self._connection_factory = connection_factory or connect

    def query_one(self, sql: str, params: Params = None) -> dict[str, Any] | None:
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    def query_all(self, sql: str, params: Params = None) -> list[dict[str, Any]]:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(self.normalize_sql(sql), tuple(params or ()))
            return _rows_to_dicts(cursor)
        finally:
            _close_cursor(cursor)
            connection.close()

    def execute(self, sql: str, params: Params = None, *, return_id: bool = False) -> int | None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            sql_to_execute = self._sql_for_insert_id(sql, return_id=return_id)
            cursor.execute(self.normalize_sql(sql_to_execute), tuple(params or ()))
            result = self._extract_insert_id(cursor, return_id=return_id)
            connection.commit()
            return result if return_id else getattr(cursor, "rowcount", None)
        except Exception as exc:
            _rollback(connection)
            raise SqlExecutionError(f"SQL execute failed: {exc}") from exc
        finally:
            _close_cursor(cursor)
            connection.close()

    def execute_many(self, sql: str, param_sets: Iterable[Sequence[Any]]) -> int | None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.executemany(self.normalize_sql(sql), [tuple(params) for params in param_sets])
            connection.commit()
            return getattr(cursor, "rowcount", None)
        except Exception as exc:
            _rollback(connection)
            raise SqlExecutionError(f"SQL execute_many failed: {exc}") from exc
        finally:
            _close_cursor(cursor)
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator["TransactionRunner"]:
        connection = self._connection_factory(self.profile)
        try:
            yield TransactionRunner(self.profile, connection)
            connection.commit()
        except Exception:
            _rollback(connection)
            raise
        finally:
            connection.close()

    def normalize_sql(self, sql: str) -> str:
        if self.profile.type in {"postgresql", "dws"}:
            return sql.replace("?", "%s")
        return sql

    def _connect(self):
        return self._connection_factory(self.profile)

    def _sql_for_insert_id(self, sql: str, *, return_id: bool) -> str:
        if not return_id or self.profile.type == "sqlite":
            return sql
        lowered = sql.lower()
        if lowered.lstrip().startswith("insert") and " returning " not in lowered:
            return f"{sql.rstrip()} RETURNING id"
        return sql

    def _extract_insert_id(self, cursor: Any, *, return_id: bool) -> int | None:
        if not return_id:
            return None
        if self.profile.type == "sqlite":
            return getattr(cursor, "lastrowid", None)
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row.get("id")
        if hasattr(row, "keys"):
            return row["id"]
        return row[0]


class TransactionRunner:
    def __init__(self, profile: DatabaseProfile, connection: Any) -> None:
        self.profile = profile
        self.connection = connection

    def query_one(self, sql: str, params: Params = None) -> dict[str, Any] | None:
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    def query_all(self, sql: str, params: Params = None) -> list[dict[str, Any]]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(self.normalize_sql(sql), tuple(params or ()))
            return _rows_to_dicts(cursor)
        finally:
            _close_cursor(cursor)

    def execute(self, sql: str, params: Params = None, *, return_id: bool = False) -> int | None:
        cursor = self.connection.cursor()
        try:
            sql_to_execute = self._sql_for_insert_id(sql, return_id=return_id)
            cursor.execute(self.normalize_sql(sql_to_execute), tuple(params or ()))
            return self._extract_insert_id(cursor, return_id=return_id) if return_id else getattr(cursor, "rowcount", None)
        finally:
            _close_cursor(cursor)

    def execute_many(self, sql: str, param_sets: Iterable[Sequence[Any]]) -> int | None:
        cursor = self.connection.cursor()
        try:
            cursor.executemany(self.normalize_sql(sql), [tuple(params) for params in param_sets])
            return getattr(cursor, "rowcount", None)
        finally:
            _close_cursor(cursor)

    def normalize_sql(self, sql: str) -> str:
        if self.profile.type in {"postgresql", "dws"}:
            return sql.replace("?", "%s")
        return sql

    def _sql_for_insert_id(self, sql: str, *, return_id: bool) -> str:
        if not return_id or self.profile.type == "sqlite":
            return sql
        lowered = sql.lower()
        if lowered.lstrip().startswith("insert") and " returning " not in lowered:
            return f"{sql.rstrip()} RETURNING id"
        return sql

    def _extract_insert_id(self, cursor: Any, *, return_id: bool) -> int | None:
        if not return_id:
            return None
        if self.profile.type == "sqlite":
            return getattr(cursor, "lastrowid", None)
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row.get("id")
        if hasattr(row, "keys"):
            return row["id"]
        return row[0]


def _rows_to_dicts(cursor: Any) -> list[dict[str, Any]]:
    columns = [description[0] for description in (cursor.description or [])]
    rows = cursor.fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            result.append(dict(row))
        elif hasattr(row, "keys"):
            result.append({key: row[key] for key in row.keys()})
        else:
            result.append(dict(zip(columns, row)))
    return result


def _close_cursor(cursor: Any) -> None:
    close = getattr(cursor, "close", None)
    if close:
        close()


def _rollback(connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        pass
