from __future__ import annotations

import sqlite3
from typing import Any

from .errors import DatabaseDriverError
from .profiles import DatabaseProfile, resolve_profile
from .tables import DEFAULT_RUNTIME_SCHEMA, render_table_tokens

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


DB_PATH = None


def _resolve_profile(profile: str | DatabaseProfile | None = None) -> DatabaseProfile:
    if isinstance(profile, DatabaseProfile):
        return profile
    if profile is None and DB_PATH is not None:
        path = str(DB_PATH)
        return DatabaseProfile("sqlite_override", "sqlite", {"type": "sqlite", "path": path, "database": path})
    return resolve_profile(profile)


def connect(profile: str | DatabaseProfile | None = None) -> Any:
    resolved = _resolve_profile(profile)
    if resolved.type == "sqlite":
        return connect_sqlite(resolved)
    if resolved.type in {"postgresql", "dws"}:
        return connect_postgresql(resolved)
    raise DatabaseDriverError(f"Unsupported database type: {resolved.type}")


def connect_sqlite(profile: DatabaseProfile) -> sqlite3.Connection:
    path = str(profile.config.get("path") or profile.config.get("database") or "").strip()
    if not path:
        raise DatabaseDriverError("SQLite profile requires 'path' or 'database'")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def connect_postgresql(profile: DatabaseProfile) -> Any:
    config = profile.config
    options = _build_pg_options(config)
    connection_options = {
        "host": config["host"],
        "port": int(config["port"]),
        "dbname": config["database"],
        "user": config["username"],
        "password": config["password"],
        "connect_timeout": int(config.get("connect_timeout", 30)),
        "options": options,
    }
    for key in ("sslmode", "application_name"):
        if config.get(key):
            connection_options[key] = str(config[key])
    if psycopg is not None:
        return psycopg.connect(**connection_options, autocommit=False)
    if psycopg2 is not None:
        connection = psycopg2.connect(**connection_options)
        connection.autocommit = False
        return connection
    raise DatabaseDriverError("PostgreSQL/DWS driver not installed. Install psycopg[binary] or psycopg2-binary.")


def _build_pg_options(config: dict[str, Any]) -> str | None:
    options: list[str] = []
    schema = str(config.get("schema") or DEFAULT_RUNTIME_SCHEMA).strip()
    if schema:
        options.append(f"-c search_path={schema}")
    statement_timeout_ms = config.get("statement_timeout_ms")
    if statement_timeout_ms is not None:
        options.append(f"-c statement_timeout={int(statement_timeout_ms)}")
    return " ".join(options) or None


class CompatRow(dict):
    def __init__(self, columns, values):
        super().__init__(zip(columns, values))
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class CompatCursor:
    def __init__(self, cursor, profile: DatabaseProfile, lastrowid=None):
        self._cursor = cursor
        self._profile = profile
        self.lastrowid = lastrowid
        self.rowcount = getattr(cursor, "rowcount", None)

    @property
    def description(self):
        return self._cursor.description

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return self._convert_row(row)

    def fetchall(self):
        return [self._convert_row(row) for row in self._cursor.fetchall()]

    def close(self):
        close = getattr(self._cursor, "close", None)
        if close:
            close()

    def _convert_row(self, row):
        if isinstance(row, CompatRow):
            return row
        if hasattr(row, "keys"):
            return CompatRow(list(row.keys()), [row[key] for key in row.keys()])
        columns = [description[0] for description in (self._cursor.description or [])]
        return CompatRow(columns, row)


class CompatConnection:
    def __init__(self, profile: str | DatabaseProfile | None = None):
        self.profile = _resolve_profile(profile)
        self._connection = connect(self.profile)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self.close()

    def execute(self, sql, params=(), expect_lastrowid=False):
        cursor = self._connection.cursor()
        sql_to_execute = self._sql_for_insert_id(sql, expect_lastrowid=expect_lastrowid)
        cursor.execute(self._normalize_sql(sql_to_execute), tuple(params or ()))
        lastrowid = self._extract_insert_id(cursor, sql_to_execute)
        return CompatCursor(cursor, self.profile, lastrowid=lastrowid)

    def executemany(self, sql, seq_of_params):
        cursor = self._connection.cursor()
        cursor.executemany(self._normalize_sql(sql), [tuple(params) for params in seq_of_params])
        return CompatCursor(cursor, self.profile)

    def executescript(self, sql_script):
        cursor = self._connection.cursor()
        for statement in split_sql_statements(render_table_tokens(sql_script, self.profile)):
            cursor.execute(self._normalize_sql(statement))
        return CompatCursor(cursor, self.profile)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()

    def _normalize_sql(self, sql):
        if self.profile.type == "sqlite":
            return render_table_tokens(sql, self.profile)
        return render_table_tokens(sql, self.profile).replace("?", "%s")

    def _sql_for_insert_id(self, sql, expect_lastrowid=False):
        if not expect_lastrowid:
            return sql
        lowered = sql.lower()
        if lowered.lstrip().startswith("insert") and " returning " not in lowered:
            return f"{sql.rstrip()} RETURNING id"
        return sql

    def _extract_insert_id(self, cursor, sql):
        if " returning " not in sql.lower():
            return None
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row.get("id")
        if hasattr(row, "keys"):
            return row["id"]
        return row[0]


def get_connection(profile: str | DatabaseProfile | None = None) -> CompatConnection:
    return CompatConnection(profile)


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    dollar_tag: str | None = None
    index = 0
    while index < len(sql_text):
        char = sql_text[index]
        next_two = sql_text[index:index + 2]
        if not in_single and not in_double and dollar_tag is None and next_two == "--":
            newline = sql_text.find("\n", index)
            if newline == -1:
                break
            current.append(sql_text[index:newline + 1])
            index = newline + 1
            continue
        if not in_single and not in_double and char == "$":
            end = index + 1
            while end < len(sql_text) and (sql_text[end].isalnum() or sql_text[end] == "_"):
                end += 1
            if end < len(sql_text) and sql_text[end] == "$":
                tag = sql_text[index:end + 1]
                current.append(tag)
                if dollar_tag == tag:
                    dollar_tag = None
                elif dollar_tag is None:
                    dollar_tag = tag
                index = end + 1
                continue
        if dollar_tag is None:
            if char == "'" and not in_double:
                in_single = not in_single
            elif char == '"' and not in_single:
                in_double = not in_double
            elif char == ";" and not in_single and not in_double:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
                index += 1
                continue
        current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements
