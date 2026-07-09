from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class WorkflowRuntimeContext:
    mods: Any
    workflow: str
    repo: str
    task_id: int
    source_payload: dict
    safe: Callable[[str, Callable[[], Any], Any], Any]
    log: Callable[[str, str], None]
    update: Callable[..., None]
    task_running: Callable[[str], None]
    task_success: Callable[..., None]
    task_skipped: Callable[..., None]
    set_partial: Callable[[str, Any], None]
    save_category_rows: Callable[[dict[str, list[dict]]], None]
    download_url: Callable[[str], str]
    build_task_meta: Callable[[dict, str, dict], dict]
    build_svn_section: Callable[[dict], dict]
    build_changes: Callable[[dict], list[dict]]
    build_conflicts: Callable[[dict], list[dict]]
    build_config_files: Callable[[list[str]], list[dict]]
    build_job_table: Callable[[Any, Any], Any]
    build_ai: Callable[[list[str], int, int], Any]
    get_active_profile_name: Callable[[], str]
    status_of: Callable[[int, int], str]
    count_levels: Callable[[list[list[dict]]], tuple[int, int]]
