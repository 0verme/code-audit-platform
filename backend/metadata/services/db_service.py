# -*- coding: utf-8 -*-
"""数据库访问降级保护层。"""
import logging

from db.profiles import get_active_profile
from svn_check.shared.db.router import select_sql_with_profile

logger = logging.getLogger("svn_check.db")


def select_sql(sql: str, profile: str | None = None):
    selected_profile = profile or get_active_profile().name
    result = select_sql_with_profile(selected_profile, sql)
    if result is None:
        logger.warning("metadata query degraded to empty result (profile=%s)", selected_profile)
        return []
    return result
