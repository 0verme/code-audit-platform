# -*- coding: utf-8 -*-
"""诊断/日志服务 —— 脱离 Streamlit 的精简替身。

真实项目的 diag_service 深度依赖 streamlit.session_state 做 rerun 诊断。
拷贝进代码审查平台（Flask 后台线程，无 Streamlit 运行时）后，这里改为
纯 logging 实现，只保留被其它模块 import 的函数签名（svn_service 用到
log_task_event / log_exception_event / log_warning_event），行为等价为
"把事件写进日志"，不影响任何规则逻辑。
"""
from __future__ import annotations

import logging
import traceback
from typing import Any

logger = logging.getLogger("svn_check.diag")


def _fmt(**fields: Any) -> str:
    return " ".join(f"{key}={value}" for key, value in fields.items())


def log_task_event(task: str, phase: str, **fields: Any) -> None:
    logger.info("[task] %s/%s %s", task, phase, _fmt(**fields))


def log_button_event(name: str, action: str, **fields: Any) -> None:
    logger.info("[button] %s/%s %s", name, action, _fmt(**fields))


def log_warning_event(event: str, **fields: Any) -> None:
    logger.warning("[warn] %s %s", event, _fmt(**fields))


def log_exception_event(event: str, exc: BaseException, **fields: Any) -> None:
    logger.error("[exception] %s %s\n%s", event, _fmt(**fields),
                 "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


# 以下函数仅为兼容真实项目调用点而保留为空操作（当前后台流程不会用到）。
def begin_app_rerun(*_args: Any, **_kwargs: Any) -> None:
    pass


def end_app_rerun(*_args: Any, **_kwargs: Any) -> None:
    pass


def run_static_risk_scan(*_args: Any, **_kwargs: Any) -> None:
    pass


def record_idle_rerun_signal(*_args: Any, **_kwargs: Any) -> None:
    pass


def log_session_state_snapshot(*_args: Any, **_kwargs: Any) -> None:
    pass


def log_widget_snapshot(*_args: Any, **_kwargs: Any) -> None:
    pass


def log_widget_changes(*_args: Any, **_kwargs: Any):
    return {}
