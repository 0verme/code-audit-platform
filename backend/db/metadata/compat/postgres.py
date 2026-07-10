# -*- coding: utf-8 -*-
"""PostgreSQL adapter backed by the unified profile format."""
from __future__ import annotations

import traceback

from db.connection import connect_postgresql
from db.profiles import ProfileConfigError, resolve_profile


def get_db_profile(profile: str | None = None):
    resolved = resolve_profile(profile)
    if resolved.type != "postgresql":
        raise ProfileConfigError(
            f"Invalid database profile '{resolved.name}': expected type postgresql, got {resolved.type}; "
            "supported types are [postgresql, dws]"
        )
    return resolved


def connect_with_profile(profile: str | None = None):
    return connect_postgresql(get_db_profile(profile))


def fetch_all(profile: str | None, sql: str):
    conn = None
    curs = None
    resolved = get_db_profile(profile)
    try:
        conn = connect_postgresql(resolved)
        curs = conn.cursor()
        curs.execute(sql)
        return curs.fetchall()
    except Exception as exc:
        print(f"select_sql exception [{resolved.name}]: {exc}")
        print(traceback.format_exc())
        return None
    finally:
        try:
            if curs is not None:
                curs.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def execute_sql(profile: str | None, sql: str, autocommit: bool = True):
    conn = None
    curs = None
    resolved = get_db_profile(profile)
    try:
        conn = connect_postgresql(resolved)
        curs = conn.cursor()
        curs.execute(sql)
        if autocommit:
            conn.commit()
        return True
    except Exception as exc:
        print(f"run_sql exception [{resolved.name}]: {exc}")
        print(traceback.format_exc())
        return False
    finally:
        try:
            if curs is not None:
                curs.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def select_sql_with_profile(profile: str | None, sql_str: str):
    return fetch_all(profile, sql_str)


def run_sql_with_profile(profile: str | None, sql_str: str):
    return execute_sql(profile, sql_str)
