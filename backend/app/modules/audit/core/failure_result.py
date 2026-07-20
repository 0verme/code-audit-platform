from __future__ import annotations

from ..source.svn import SvnCliNotFoundError

SVN_CLI_MISSING_HINT = "（未找到 svn 命令行客户端，请安装 SVN 并加入 PATH）"


def build_failure_result(error: BaseException | str, *, source_type: str) -> dict:
    message = str(error)
    if source_type == "svn" and isinstance(error, SvnCliNotFoundError):
        message += SVN_CLI_MISSING_HINT
    return {"status": "fail", "error": message}


def build_engine_load_failure_result(import_error: str | None) -> dict:
    return {"status": "fail", "error": f"真实审查引擎加载失败。\n{import_error}"}
