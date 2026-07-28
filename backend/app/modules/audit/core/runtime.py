from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RunProgress:
    log: Callable[[str, str], None]
    update: Callable[..., None]
    task_running: Callable[[str], None]
    task_success: Callable[..., None]
    task_skipped: Callable[..., None]
    set_partial: Callable[[str, Any], None]


@dataclass(frozen=True)
class AuditServices:
    mods: Any
    safe: Callable[[str, Callable[[], Any], Any], Any]
    save_category_rows: Callable[[dict[str, list[dict]]], None]
    download_url: Callable[[str], str]
    build_ai: Callable[..., Any]
    get_active_profile_name: Callable[[], str]


@dataclass(frozen=True)
class ReportSupport:
    build_task_meta: Callable[[dict, str, dict], dict]
    build_svn_section: Callable[[dict], dict]
    build_changes: Callable[[dict], list[dict]]
    build_conflicts: Callable[[dict], list[dict]]
    build_lineage_summary: Callable[..., dict]
    build_config_files: Callable[[list[str]], list[dict]]
    build_job_table: Callable[[Any, Any], Any]
    status_of: Callable[[int, int], str]
    count_levels: Callable[[list[list[dict]]], tuple[int, int]]
    build_source_file: Callable[..., dict | None] | None = None


@dataclass(frozen=True)
class HcytServices:
    collect_input_files: Callable[..., Any]
    build_source_classified_progress: Callable[..., Any]
    publish_progress: Callable[..., Any]
    run_rules: Callable[..., Any]
    run_inspections: Callable[..., Any]
    run_ai_review: Callable[..., Any]
    sync_legacy_results: Callable[..., Any]
    build_report: Callable[..., dict]
    run_schedule: Callable[..., Any]
    run_programs: Callable[..., Any]


@dataclass(frozen=True)
class WorkflowRuntimeContext:
    workflow: str
    repo: str
    task_id: int
    ai_enabled: bool
    source_payload: dict
    progress: RunProgress
    services: AuditServices
    reports: ReportSupport
    hcyt: HcytServices | None = None

    @classmethod
    def from_legacy(cls, **values):
        """Test/compatibility factory while callers migrate to explicit ports."""

        hcyt = HcytServices(
            collect_input_files=values.pop("collect_hcyt_input_files"),
            build_source_classified_progress=values.pop("build_source_classified_progress"),
            publish_progress=values.pop("publish_hcyt_progress"),
            run_rules=values.pop("run_hcyt_rules"),
            run_inspections=values.pop("run_hcyt_inspections"),
            run_ai_review=values.pop("run_hcyt_ai_review"),
            sync_legacy_results=values.pop("sync_hcyt_legacy_results"),
            build_report=values.pop("build_hcyt_report"),
            run_schedule=values.pop("run_hcyt_schedule"),
            run_programs=values.pop("run_hcyt_programs"),
        )
        progress = RunProgress(
            log=values.pop("log"),
            update=values.pop("update"),
            task_running=values.pop("task_running"),
            task_success=values.pop("task_success"),
            task_skipped=values.pop("task_skipped"),
            set_partial=values.pop("set_partial"),
        )
        services = AuditServices(
            mods=values.pop("mods"),
            safe=values.pop("safe"),
            save_category_rows=values.pop("save_category_rows"),
            download_url=values.pop("download_url"),
            build_ai=values.pop("build_ai"),
            get_active_profile_name=values.pop("get_active_profile_name"),
        )
        reports = ReportSupport(
            build_task_meta=values.pop("build_task_meta"),
            build_svn_section=values.pop("build_svn_section"),
            build_changes=values.pop("build_changes"),
            build_conflicts=values.pop("build_conflicts"),
            build_lineage_summary=values.pop("build_lineage_summary"),
            build_config_files=values.pop("build_config_files"),
            build_job_table=values.pop("build_job_table"),
            status_of=values.pop("status_of"),
            count_levels=values.pop("count_levels"),
            build_source_file=values.pop("build_source_file", None),
        )
        return cls(progress=progress, services=services, reports=reports, hcyt=hcyt, **values)
