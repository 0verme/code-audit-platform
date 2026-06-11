# -*- coding: utf-8 -*-
# !/bin/python
from __future__ import annotations

import traceback
from pathlib import Path

import yaml

# 降级保护：JDBC 桥（jaydebeapi/JVM）在无行内库的环境可能缺失。
# 这里容忍 import 失败，让模块照常加载；真正 connect 时才报错，
# 并被 fetch_all 的 try/except 兜住 -> 返回 None -> db_service 归一为空集。
try:
    import jaydebeapi
except Exception:  # pragma: no cover - 取决于部署环境是否装了 JDBC 桥
    jaydebeapi = None


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / 'configs' / 'database.yaml'
DEFAULT_DRIVER = 'com.huawei.gauss200.jdbc.Driver'
DEFAULT_JAR = ROOT_DIR / 'resources' / 'jars' / 'gaussdb200.jar'


def load_db_profiles() -> dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    defaults = data.get('defaults', {})
    profiles = data.get('profiles', {})
    merged = {}
    for name, profile in profiles.items():
        config = dict(defaults)
        config.update(profile)
        merged[name] = config
    return merged


def get_db_profile(profile: str) -> dict:
    profiles = load_db_profiles()
    if profile not in profiles:
        raise KeyError(f'database profile not found: {profile}')

    config = dict(profiles[profile])
    config.setdefault('driver', DEFAULT_DRIVER)
    configured_jar_path = Path(config.get('jar_path', DEFAULT_JAR))
    config['jar_path'] = str(configured_jar_path if configured_jar_path.exists() else DEFAULT_JAR)
    return config


def connect_with_profile(profile: str):
    if jaydebeapi is None:
        raise RuntimeError('jaydebeapi/JVM 不可用，无法连接行内 GaussDB')
    config = get_db_profile(profile)
    return jaydebeapi.connect(
        config['driver'],
        config['jdbc_url'],
        [config['user'], config['password']],
        config['jar_path'],
    )


def _is_autocommit_enabled(conn) -> bool | None:
    jconn = getattr(conn, 'jconn', None)
    if jconn is None:
        return None
    try:
        return bool(jconn.getAutoCommit())
    except Exception:
        return None


def _commit_if_needed(conn):
    auto_commit_enabled = _is_autocommit_enabled(conn)
    if auto_commit_enabled is True:
        return

    try:
        conn.commit()
        return
    except Exception as e:
        if 'autoCommit is enabled' in str(e):
            return

        jconn = getattr(conn, 'jconn', None)
        if jconn is None:
            raise

        try:
            jconn.commit()
        except Exception as inner_e:
            if 'autoCommit is enabled' in str(inner_e):
                return
            raise inner_e from e


def fetch_all(profile: str, sql: str):
    conn = None
    curs = None
    try:
        conn = connect_with_profile(profile)
        curs = conn.cursor()
        curs.execute(sql)
        return curs.fetchall()
    except Exception as e:
        print(f'select_sql exception [{profile}]:', e)
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


def execute_sql(profile: str, sql: str, autocommit: bool = True):
    conn = None
    curs = None
    try:
        conn = connect_with_profile(profile)
        curs = conn.cursor()
        curs.execute(sql)
        if autocommit:
            _commit_if_needed(conn)
        return True
    except Exception as e:
        print(f'run_sql exception [{profile}]:', e)
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


def select_sql_with_profile(profile: str, sql_str: str):
    return fetch_all(profile, sql_str)


def run_sql_with_profile(profile: str, sql_str: str):
    return execute_sql(profile, sql_str)
