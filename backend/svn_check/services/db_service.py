# -*- coding: utf-8 -*-
# !/bin/python
"""数据库访问入口 —— 降级保护层。

照搬自真实项目，规则逻辑零改动。唯一新增：行内 GaussDB 连不上时
（底层 fetch_all 返回 None），这里归一为空集并打日志，让纯静态规则
继续执行，而不是让 `for row in select_sql(...)` 直接崩溃。
"""
import logging

from shared.db.router import select_sql_with_profile

logger = logging.getLogger("svn_check.db")


def select_sql(sql: str, profile: str = 'czcb'):
    result = select_sql_with_profile(profile, sql)
    if result is None:
        logger.warning("行内数据库查询失败，已降级返回空集（profile=%s）", profile)
        return []
    return result
