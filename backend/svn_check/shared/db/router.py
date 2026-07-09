# -*- coding: utf-8 -*-
"""统一数据库路由：平台运行库与元数据访问共用同一 profile 解析入口。"""
from __future__ import annotations

from functools import lru_cache

from db.profiles import DatabaseProfile, resolve_profile


def _resolve(profile: str | None = None) -> DatabaseProfile:
    return resolve_profile(profile)


def get_backend(profile: str | None = None) -> str:
    return _resolve(profile).type


@lru_cache(maxsize=2)
def _module_for_type(db_type: str):
    if db_type == "postgresql":
        from shared.db import postgres

        return postgres
    if db_type == "dws":
        from shared.db import gaussdb

        return gaussdb
    raise RuntimeError(f"Unsupported database type in router: {db_type}")


def _impl(profile: str | None = None):
    return _module_for_type(_resolve(profile).type)


def select_sql_with_profile(profile: str | None, sql_str: str):
    resolved = _resolve(profile)
    return _impl(resolved.name).select_sql_with_profile(resolved.name, sql_str)


def run_sql_with_profile(profile: str | None, sql_str: str):
    resolved = _resolve(profile)
    return _impl(resolved.name).run_sql_with_profile(resolved.name, sql_str)
