# -*- coding: utf-8 -*-
"""数据库后端路由：根据配置在 Postgres / GaussDB 之间分发。

选择优先级：环境变量 SVN_CHECK_DB_BACKEND > configs/database.yaml 的 backend 段 > 'gaussdb'。
对外暴露与 gaussdb 一致的 select_sql_with_profile / run_sql_with_profile，
便于 db_service、mapping_sqlite 等调用点无感切换。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "database.yaml"


@lru_cache(maxsize=1)
def get_backend() -> str:
    env = os.getenv("SVN_CHECK_DB_BACKEND")
    if env:
        return env.strip().lower()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return str(data.get("backend", "gaussdb")).strip().lower()
    except Exception:
        return "gaussdb"


def _impl():
    if get_backend() == "postgres":
        from shared.db import postgres
        return postgres
    from shared.db import gaussdb
    return gaussdb


def select_sql_with_profile(profile: str, sql_str: str):
    return _impl().select_sql_with_profile(profile, sql_str)


def run_sql_with_profile(profile: str, sql_str: str):
    return _impl().run_sql_with_profile(profile, sql_str)
