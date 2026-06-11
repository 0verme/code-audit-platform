# -*- coding: utf-8 -*-
"""Postgres 接入层（测试环境）。

与 gaussdb.py 对齐的最小接口：select_sql_with_profile / run_sql_with_profile，
连接参数读取 configs/database.yaml 的 postgres 段。失败时返回 None（由上层
db_service 降级为空集），与 GaussDB 行为一致。
"""
from __future__ import annotations

import os
import traceback
from pathlib import Path

import yaml

# psycopg3 优先，回退 psycopg2。
try:
    import psycopg as _pg
    _PG_KIND = "psycopg3"
except Exception:  # pragma: no cover
    try:
        import psycopg2 as _pg
        _PG_KIND = "psycopg2"
    except Exception:
        _pg = None
        _PG_KIND = None

ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "configs" / "database.yaml"


def load_pg_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    config = dict(data.get("postgres", {}))
    # 环境变量可覆盖（便于不同环境部署）
    overrides = {
        "host": "SVN_CHECK_PG_HOST",
        "port": "SVN_CHECK_PG_PORT",
        "dbname": "SVN_CHECK_PG_DB",
        "user": "SVN_CHECK_PG_USER",
        "password": "SVN_CHECK_PG_PASSWORD",
        "schema": "SVN_CHECK_PG_SCHEMA",
    }
    for key, env_name in overrides.items():
        value = os.getenv(env_name)
        if value:
            config[key] = value
    return config


def connect():
    if _pg is None:
        raise RuntimeError("未安装 psycopg/psycopg2，无法连接 Postgres")
    config = load_pg_config()
    return _pg.connect(
        host=config.get("host", "127.0.0.1"),
        port=int(config.get("port", 5432)),
        dbname=config.get("dbname", "postgres"),
        user=config.get("user", "postgres"),
        password=config.get("password", ""),
        connect_timeout=int(config.get("connect_timeout", 15)),
    )


def fetch_all(sql: str):
    conn = None
    cur = None
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql)
        return cur.fetchall()
    except Exception as exc:
        print(f"pg select exception: {exc}")
        print(traceback.format_exc())
        return None
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass


def select_sql_with_profile(profile: str, sql_str: str):
    # profile 参数为兼容 GaussDB 接口签名；Postgres 测试环境只有单库。
    return fetch_all(sql_str)


def run_sql_with_profile(profile: str, sql_str: str) -> bool:
    conn = None
    cur = None
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute(sql_str)
        conn.commit()
        return True
    except Exception as exc:
        print(f"pg run exception: {exc}")
        print(traceback.format_exc())
        return False
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            if conn is not None:
                conn.close()
        except Exception:
            pass
