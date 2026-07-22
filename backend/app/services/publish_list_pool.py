from __future__ import annotations

import atexit
import os
import queue
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from app.db.connection import connect


PUBLISH_LIST_POOL_SIZE_ENV = "PUBLISH_LIST_READ_POOL_SIZE"
_pool_lock = threading.Lock()
_pools: dict[tuple[str, str], queue.LifoQueue] = {}


def _pool_size() -> int:
    try:
        return max(1, int(os.getenv(PUBLISH_LIST_POOL_SIZE_ENV, "4")))
    except ValueError:
        return 4


def _pool_key(profile: Any) -> tuple[str, str]:
    return str(profile.name), str(profile.type)


def _pool(profile: Any) -> queue.LifoQueue:
    key = _pool_key(profile)
    with _pool_lock:
        pool = _pools.get(key)
        if pool is None:
            pool = queue.LifoQueue(maxsize=_pool_size())
            _pools[key] = pool
        return pool


def _connection_is_open(connection: Any) -> bool:
    jdbc_connection = getattr(connection, "jconn", None)
    if jdbc_connection is not None:
        try:
            return not bool(jdbc_connection.isClosed())
        except Exception:
            return False
    try:
        return not bool(getattr(connection, "closed", False))
    except Exception:
        return False


def _close_connection(connection: Any) -> None:
    try:
        connection.close()
    except Exception:
        pass


def _prepare_read_connection(connection: Any) -> Any:
    jdbc_connection = getattr(connection, "jconn", None)
    if jdbc_connection is not None:
        try:
            jdbc_connection.setAutoCommit(True)
        except Exception:
            pass
    else:
        try:
            connection.autocommit = True
        except Exception:
            pass
    return connection


def _acquire(profile: Any) -> Any:
    pool = _pool(profile)
    while True:
        try:
            connection = pool.get_nowait()
        except queue.Empty:
            return _prepare_read_connection(connect(profile))
        if _connection_is_open(connection):
            return _prepare_read_connection(connection)
        _close_connection(connection)


def _release(profile: Any, connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        _close_connection(connection)
        return
    if not _connection_is_open(connection):
        _close_connection(connection)
        return
    try:
        _pool(profile).put_nowait(connection)
    except queue.Full:
        _close_connection(connection)


@contextmanager
def publish_list_connection(profile: Any) -> Iterator[Any]:
    connection = _acquire(profile)
    reusable = False
    try:
        yield connection
        reusable = True
    finally:
        if reusable:
            _release(profile, connection)
        else:
            _close_connection(connection)


def close_publish_list_connections() -> None:
    with _pool_lock:
        pools = list(_pools.values())
        _pools.clear()
    for pool in pools:
        while True:
            try:
                connection = pool.get_nowait()
            except queue.Empty:
                break
            _close_connection(connection)


atexit.register(close_publish_list_connections)
