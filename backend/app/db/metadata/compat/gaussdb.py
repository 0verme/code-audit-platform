# -*- coding: utf-8 -*-
"""DWS adapter backed by the unified profile format.

Uses the Huawei GaussDB JDBC driver through JayDeBeApi.
"""
from __future__ import annotations

import atexit
import os
import queue
import threading
import traceback

from app.db.connection import connect_dws
from app.db.profiles import ProfileConfigError, resolve_profile


METADATA_POOL_SIZE_ENV = "CODE_AUDIT_DWS_METADATA_POOL_SIZE"
_read_pool_lock = threading.Lock()
_read_pools: dict[str, queue.LifoQueue] = {}


def get_db_profile(profile: str | None = None):
    resolved = resolve_profile(profile)
    if resolved.type != "dws":
        raise ProfileConfigError(
            f"Invalid database profile '{resolved.name}': expected type dws, got {resolved.type}; "
            "supported types are [postgresql, dws]"
        )
    return resolved


def connect_with_profile(profile: str | None = None):
    return connect_dws(get_db_profile(profile))


def _pool_size() -> int:
    try:
        return max(1, int(os.getenv(METADATA_POOL_SIZE_ENV, "4")))
    except ValueError:
        return 4


def _read_pool(profile_name: str) -> queue.LifoQueue:
    with _read_pool_lock:
        pool = _read_pools.get(profile_name)
        if pool is None:
            pool = queue.LifoQueue(maxsize=_pool_size())
            _read_pools[profile_name] = pool
        return pool


def _connection_is_open(conn) -> bool:
    jconn = getattr(conn, "jconn", None)
    if jconn is not None:
        try:
            return not bool(jconn.isClosed())
        except Exception:
            pass
    closed = getattr(conn, "closed", False)
    return not bool(closed)


def _close_connection(conn) -> None:
    try:
        conn.close()
    except Exception:
        pass


def _acquire_read_connection(resolved):
    pool = _read_pool(resolved.name)
    while True:
        try:
            conn = pool.get_nowait()
        except queue.Empty:
            return connect_dws(resolved), False
        if _connection_is_open(conn):
            return conn, True
        _close_connection(conn)


def _release_read_connection(resolved, conn) -> None:
    try:
        conn.rollback()
    except Exception:
        _close_connection(conn)
        return
    if not _connection_is_open(conn):
        _close_connection(conn)
        return
    try:
        _read_pool(resolved.name).put_nowait(conn)
    except queue.Full:
        _close_connection(conn)


def close_metadata_connections() -> None:
    with _read_pool_lock:
        pools = list(_read_pools.values())
        _read_pools.clear()
    for pool in pools:
        while True:
            try:
                conn = pool.get_nowait()
            except queue.Empty:
                break
            _close_connection(conn)


atexit.register(close_metadata_connections)


def fetch_all(profile: str | None, sql: str):
    resolved = get_db_profile(profile)
    for _attempt in range(2):
        conn = None
        curs = None
        reused = False
        reusable = False
        try:
            conn, reused = _acquire_read_connection(resolved)
            curs = conn.cursor()
            curs.execute(sql)
            rows = curs.fetchall()
            reusable = True
            return rows
        except Exception as exc:
            if not reused:
                print(f"select_sql exception [{resolved.name}]: {exc}")
                print(traceback.format_exc())
                return None
        finally:
            try:
                if curs is not None:
                    curs.close()
            except Exception:
                pass
            if conn is not None:
                if reusable:
                    _release_read_connection(resolved, conn)
                else:
                    _close_connection(conn)
    return None


def execute_sql(profile: str | None, sql: str, autocommit: bool = True):
    conn = None
    curs = None
    resolved = get_db_profile(profile)
    try:
        conn = connect_dws(resolved)
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
