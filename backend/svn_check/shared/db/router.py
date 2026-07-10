# -*- coding: utf-8 -*-
"""Metadata DB compatibility shim for shared profile-based routing."""
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


def _resolve_backend(profile: str | None = None) -> tuple[DatabaseProfile, object]:
    """Resolve the metadata backend module without changing compat semantics."""

    resolved = _resolve(profile)
    return resolved, _impl(resolved.name)


def select_sql_with_profile(profile: str | None, sql_str: str):
    resolved, backend = _resolve_backend(profile)
    return backend.select_sql_with_profile(resolved.name, sql_str)


def run_sql_with_profile(profile: str | None, sql_str: str):
    resolved, backend = _resolve_backend(profile)
    return backend.run_sql_with_profile(resolved.name, sql_str)
