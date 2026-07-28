from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path
from urllib.parse import quote

import pandas as pd


def get_export_base():
    env_path = os.getenv("SVN_CHECK_EXPORT_BASE")
    if env_path:
        return Path(env_path)
    if sys.platform == "linux":
        return Path("/home/pytool/pytool/tmp")
    return Path(r"E:\svn测试")


def get_export_http_root():
    return os.getenv("SVN_CHECK_DOWNLOAD_ROOT", "https://example.com/downloads")


def build_export_download_url(path_str):
    export_base = get_export_base()
    path_obj = Path(path_str)
    try:
        rel_path = path_obj.relative_to(export_base)
    except ValueError:
        return ""
    quoted_rel_path = "/".join(quote(part) for part in rel_path.parts)
    return f"{get_export_http_root().rstrip('/')}/{quoted_rel_path}"


def build_export_download_link(path_str, label="下载代码"):
    download_url = build_export_download_url(path_str)
    if not download_url:
        return ""
    return f'<a href="{download_url}" target="_blank">{label}</a>'


def safe_remove_prefix(path_str):
    path = Path(path_str)
    try:
        return str(path.relative_to(get_export_base()))
    except ValueError:
        return path_str


def get_filename(path_str):
    return Path(path_str).name


def normalize_path(path_str):
    if pd.isna(path_str) or not str(path_str).strip():
        return None
    normalized = str(path_str).strip().replace("\\", "/")
    if len(normalized) >= 2 and normalized[1] == ":":
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.lower()


def tail_path(path_str, levels=3):
    normalized = normalize_path(path_str)
    if not normalized:
        return None
    return "/".join(normalized.split("/")[-levels:])


def match_path(path, pattern):
    return fnmatch.fnmatch(Path(path).as_posix(), pattern)


def match_any(path, patterns):
    normalized = Path(path).as_posix()
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)
