# -*- coding: utf-8 -*-
"""审查引擎编排层。

调用拷贝进本仓库的真实规则引擎（backend/svn_check/），把 SVN 拉取 + 规则
检查的结果，整理成「与 Streamlit 版展示内容对齐」的结构化报告（report JSON），
供前端逐栏渲染。

设计原则：
- 规则逻辑完全复用 svn_check 内的源码，本层只做编排和"把 Streamlit 里展示
  的东西收集进 JSON"（调度清单表格、config JSON 表格、预览/下载链接、
  结果表禁用/源系统标注、帆软引擎标志等）；
- 行内 GaussDB / 血缘库连不上时由 db_service 降级层兜底返回空集，依赖数据库
  的展示信息（结果表登记、禁用标注等）自动弱化，纯静态规则照常输出。
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from .compat import build_legacy_hcyt_audit_result_rows, build_legacy_nups_audit_result_rows
from .fine_runner import run_fine as _run_fine
from .hcyt_runner import run_hcyt as _run_hcyt
from .hcyt_ai_review import run_hcyt_ai_review
from .hcyt_file_classifier import collect_hcyt_input_files
from .hcyt_inspection_orchestrator import run_hcyt_inspections
from .hcyt_rule_runner import run_hcyt_rules
from .hcyt_progress_events import build_source_classified_progress, publish_hcyt_progress
from .hcyt_report_builder import build_hcyt_report
from .hcyt_legacy_result_sync import sync_hcyt_legacy_results
from .hcyt_subworkflow_runtime import (
    run_hcyt_programs as _run_hcyt_programs,
    run_hcyt_schedule as _run_hcyt_schedule,
)
from .nups_report_builder import build_nups_report
from .nups_runner import run_nups as _run_nups
from .lineage_payload import empty_lineage_summary, json_safe, lineage_warning
from .report_builder import (
    build_ai as _build_ai,
    build_changes as _build_changes,
    build_config_files as _build_config_files,
    build_conflicts as _build_conflicts,
    build_job_table as _build_job_table,
    build_task_meta as _build_task_meta,
)
from .result_table_annotations import (
    annotate_table as _annotate_table,
    load_result_table_annotations as _load_result_table_annotations,
)
from .result_normalizer import (
    dedupe_tables,
    format_duration,
    normalize_table,
    rule_label,
    text_to_messages,
    text_to_rows,
)
from .run_failure_result import build_engine_load_failure_result, build_failure_result
from .run_result_finalizer import finalize_run_result
from .run_registry import (
    _run_states,
    create_audit_run_state as _create_audit_run_state,
    get_audit_run_partial_result as _get_audit_run_partial_result,
    get_audit_run_state as _get_audit_run_state,
    get_audit_run_status as _get_audit_run_status,
)
from .source_resolver import (
    build_source_label,
    build_source_load_step,
    build_source_summary,
    detect_workflow,
    resolve_workspace,
    resolve_workflow,
)
from .source_download import build_source_download_url, source_relative_paths, source_relative_paths_from_changes
from .workflow_dispatcher import WorkflowRunContext, run_workflow
from .workflow_runtime import WorkflowRuntimeContext
from app.db.profiles import get_active_profile
from app.db.runtime_store import (
    persist_task_completion_atomic,
    persist_task_run_completion,
    replace_audit_results,
    update_task_runtime_state,
)

_empty_lineage_summary = empty_lineage_summary

try:
    from .run import AuditRunState, AuditTask, AuditTaskStatus
except ImportError:  # pragma: no cover - direct module execution fallback
    from run import AuditRunState, AuditTask, AuditTaskStatus

# 把拷贝进来的真实项目加入模块搜索路径，保持其内部 `from core...`、
# `from services...`、`from shared...` 等绝对导入原样可用。

CALE_MAP = {
    "SYS_MONTH_END_CALENDAR": "每月末",
    "SYS_EVERYDAY_CALENDAR": "每日",
}

# 与 svn_check/ui/public_stream.py 中保持一致的重点源系统（结果表标红用）。
HIGHLIGHT_RESULT_SOURCE_SYSTEMS = {
    "二代评分卡", "IPC系统", "统一授信", "押品系统",
    "信用风险预警", "回检系统", "移动贷后", "老信贷系统",
}

WORKFLOW_NAMES = {
    "hcyt": "HCYT 湖仓审查",
    "nups": "NUPS 统一支付审查",
    "fine-report": "FineReport 报表审查",
}

_load_lock = threading.Lock()
_mods = None
_import_error: str | None = None


DEFAULT_AUDIT_TASKS = (
    AuditTask("source_load", "读取工作区 / SVN"),
    AuditTask("classify_files", "文件分类", dependencies=("source_load",)),
    AuditTask("trunk_conflicts", "trunk 冲突检查", dependencies=("classify_files",)),
    AuditTask("dws_sql", "DWS SQL 检查", dependencies=("classify_files",), weight=2),
    AuditTask("hive_sql", "Hive SQL 检查", dependencies=("classify_files",), weight=2),
    AuditTask("config_files", "配置文件检查", dependencies=("classify_files",)),
    AuditTask("post_scripts", "后置脚本检查", dependencies=("classify_files",)),
    AuditTask("recv_config", "收卸配置检查", dependencies=("classify_files",)),
    AuditTask("schedule", "调度表检查", dependencies=("classify_files",), weight=2),
    AuditTask("python_scripts", "Python 脚本检查", dependencies=("schedule",), weight=2),
    AuditTask("lineage", "依赖链分析", dependencies=("schedule", "python_scripts"), weight=2),
    AuditTask("summary", "汇总审查结果", dependencies=("trunk_conflicts", "dws_sql", "hive_sql", "config_files", "post_scripts", "recv_config", "schedule", "python_scripts", "lineage")),
)


# ---------------------------------------------------------------------------
# 真实模块加载
# ---------------------------------------------------------------------------

def _load_real_modules():
    global _mods, _import_error
    with _load_lock:
        if _mods is not None or _import_error is not None:
            return
        try:
            import types as _types

            from app.modules.audit.checks.svn_service import svn_main
            from app.modules.audit.checks.ai_service import call_sql_llm
            from app.modules.audit.checks import re_service
            from app.modules.metadata.services import audit_metadata_service
            from app.modules.audit.checks.workspace_service import load_local_workspace
            from app.modules.audit.checks import hcyt
            from app.modules.audit.checks import nups_rule
            from app.modules.audit.checks import fine_rule
            from app.modules.metadata.services import public_data
            from app.modules.audit.rules.asset_issue import asset_issues_to_unified_issues, dedupe_issues
            from app.modules.audit.checks.hcyt import ddl_rule as hcyt_ddl_rule
            from app.modules.audit.checks.hcyt import python_rule as hcyt_python_rule
            from app.modules.audit.checks.hcyt import sql_rule as hcyt_sql_rule
            from app.modules.lineage.mapping_compat import load_registered_result_tables

            _mods = _types.SimpleNamespace(
                svn_main=svn_main,
                load_local_workspace=load_local_workspace,
                call_sql_llm=call_sql_llm,
                re_service=re_service,
                audit_metadata_service=audit_metadata_service,
                hcyt=hcyt,
                hcyt_ddl_rule=hcyt_ddl_rule,
                hcyt_sql_rule=hcyt_sql_rule,
                hcyt_python_rule=hcyt_python_rule,
                nups_rule=nups_rule,
                fine_rule=fine_rule,
                public_data=public_data,
                dedupe_issues=dedupe_issues,
                asset_issues_to_unified_issues=asset_issues_to_unified_issues,
                load_registered_result_tables=load_registered_result_tables,
            )
        except Exception:
            _import_error = traceback.format_exc()


# ---------------------------------------------------------------------------
# 任务执行
# ---------------------------------------------------------------------------


def create_audit_run_state(task_id: int, workflow: str) -> AuditRunState:
    return _create_audit_run_state(task_id, workflow, DEFAULT_AUDIT_TASKS)


def get_audit_run_state(task_id: int) -> AuditRunState | None:
    return _get_audit_run_state(task_id)


def get_audit_run_status(task_id: int) -> dict | None:
    return _get_audit_run_status(task_id)


def get_audit_run_partial_result(task_id: int) -> dict | None:
    return _get_audit_run_partial_result(task_id)


def _build_lineage_summary_payload(m, job_df=None, program_xls=None, py_lists=None, db_job_rows=None, log_timing=None):
    import time

    def timed(label, fn, **fields):
        started = time.perf_counter()
        if log_timing is not None:
            log_timing(label, "start", **fields)
        try:
            return fn()
        finally:
            if log_timing is not None:
                log_timing(label, "end", elapsed_ms=round((time.perf_counter() - started) * 1000, 1), **fields)

    warnings = []
    merge_df = None
    job_outfile_lookup = {}
    metadata_service = getattr(m, "audit_metadata_service", None)

    if metadata_service is None:
        warnings.append("job metadata unavailable")
    else:
        try:
            job_outfile_rows = timed("lineage.load_job_outfiles", lambda: metadata_service.list_job_outfiles() or [])
            job_outfile_lookup = m.re_service.build_job_outfile_lookup(job_outfile_rows)
        except Exception as exc:
            warnings.append(lineage_warning("job outfile metadata", exc))
            job_outfile_lookup = {}

    if job_df is not None and program_xls:
        try:
            program_df = timed("lineage.load_program_excel", lambda: m.re_service.load_xls_to_df(program_xls))
            merge_job = timed("lineage.normalize_job", lambda: m.hcyt.all_job_df(job_df, db_job_rows)) if db_job_rows is not None else job_df
            try:
                merge_program = timed("lineage.normalize_program", lambda: m.hcyt.all_program_df(program_df))
            except Exception:
                merge_program = program_df
            merge_df = timed("lineage.merge_job_program", lambda: m.re_service.merge_job_program(merge_job, merge_program))
        except Exception as exc:
            warnings.append(lineage_warning("merge metadata", exc))
    elif job_df is None:
        warnings.append("job metadata unavailable")

    try:
        summary = timed(
            "lineage.build_wide_summary",
            lambda: m.re_service.build_wide_table_lineage_summary(
                merge_df=merge_df,
                input_path=None,
                job_outfile_lookup=job_outfile_lookup,
                metadata_service=metadata_service,
                log_timing=log_timing,
            ),
        )
    except Exception as exc:
        summary = empty_lineage_summary([lineage_warning("lineage summary", exc)])

    summary = json_safe(summary)
    if not isinstance(summary, dict):
        summary = empty_lineage_summary(["lineage summary unavailable"])
    for key in ("resultTables", "jobs", "recvPlans", "sysNames", "outfiles", "warnings"):
        if not isinstance(summary.get(key), list):
            summary[key] = []
    if not isinstance(summary.get("stats"), dict):
        summary["stats"] = {}
    for warning in warnings:
        if warning not in summary["warnings"]:
            summary["warnings"].append(warning)
    return summary


class TaskRun:
    def __init__(
        self,
        task_id,
        repo,
        workflow,
        ai_enabled=False,
        debug_enabled=False,
        author="local-user",
        source_type="svn",
    ):
        self.task_id = task_id
        self.repo = repo
        self.workflow = workflow
        self.ai_enabled = bool(ai_enabled)
        self.debug_enabled = bool(debug_enabled)
        self.author = author
        self.source_type = (source_type or "svn").lower()
        self.logs = []
        self.start_ts = time.time()
        self.run_state = create_audit_run_state(task_id, workflow)
        self.run_state.mark_running()
        self._source_download_paths = {}
        self._source_download_by_relative = {}

    # ---- 日志 / 进度 ----

    def _ensure_run_state(self):
        if not hasattr(self, "run_state"):
            self.run_state = create_audit_run_state(self.task_id, self.workflow)
            self.run_state.mark_running()
        return self.run_state

    def log(self, msg, level="INFO", detail=False):
        message = str(msg)
        is_detail = detail or message.startswith("[timing]") or message.startswith("Traceback (most recent call last):")
        if is_detail and not self.debug_enabled:
            return
        entry = {"ts": datetime.now().strftime("%H:%M:%S"), "level": level, "msg": message}
        self.logs.append(entry)
        self._ensure_run_state().add_log(message, level=level)
        print(f"[task {self.task_id}] {level} {message}", flush=True)

    def update(self, progress=None, step=None):
        update_task_runtime_state(
            self.task_id,
            json.dumps(self.logs, ensure_ascii=False),
            progress=progress,
            step=step,
        )
        if step:
            self.log(f"当前步骤：{step}")

    def task_running(self, key):
        state = self._ensure_run_state().get_task(key)
        if state.status == AuditTaskStatus.QUEUED:
            state.mark_running()

    def task_success(self, key, result=None, summary=None):
        state = self._ensure_run_state().get_task(key)
        if not state.is_terminal:
            state.mark_success(result=result, summary=summary)

    def task_skipped(self, key, reason=""):
        state = self._ensure_run_state().get_task(key)
        if not state.is_terminal:
            state.mark_skipped(reason)

    def set_partial(self, key, value):
        self._ensure_run_state().set_section(key, value)

    def safe(self, label, fn, default):
        """外部依赖（行内库/血缘库/Excel 读取）的降级封装。"""
        try:
            return fn()
        except Exception as exc:
            self.log(f"{label} 不可用，已降级跳过: {exc}", "WARN")
            return default

    def finish(self, status, report=None, error=None):
        duration = format_duration(time.time() - self.start_ts)
        finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.workflow in {"hcyt", "nups"} and report is not None:
            # Both workflows have complete reports and final legacy-result
            # projections on this path. Keep every completion fact in the
            # repository transaction.
            audit_results = (
                build_legacy_hcyt_audit_result_rows(report)
                if self.workflow == "hcyt"
                else build_legacy_nups_audit_result_rows(report.get("sqlChecks", []), rule_label)
            )
            try:
                persist_task_completion_atomic(
                    self.task_id,
                    status=status,
                    duration=duration,
                    finished_at=finished_at,
                    error=error,
                    progress=100,
                    step="completed",
                    logs=self.logs,
                    report=report,
                    audit_results=audit_results,
                )
            except Exception:
                # TaskRun.run() must not turn a failed atomic completion into a
                # legacy, non-atomic completion attempt.
                self._atomic_completion_failed = True
                raise

            # Completion is published only after the DB commit.
            self.set_partial("finalReport", report)
            self.task_success("summary", summary={"status": status})
            self._ensure_run_state().mark_finished()
            return

        if report is not None:
            self.set_partial("finalReport", report)
            self.task_success("summary", summary={"status": status})
            self._ensure_run_state().mark_finished()
        else:
            self._ensure_run_state().mark_finished(error=error or status)
        persist_task_run_completion(
            self.task_id,
            status=status,
            duration=duration,
            finished_at=finished_at,
            error=error,
            progress=100 if report else 0,
            step="completed" if report else "failed",
            logs=self.logs,
            report=report,
        )

    def save_category_rows(self, grouped_rows):
        """Sync audit_results to preserve the legacy /api/audit-results endpoint."""
        replace_audit_results(self.task_id, grouped_rows)


    # ---- 主入口 ----

    def build_workflow_runtime(self, svn_result):
        return WorkflowRuntimeContext(
            mods=_mods,
            workflow=self.workflow,
            repo=self.repo,
            task_id=self.task_id,
            ai_enabled=getattr(self, "ai_enabled", False),
            source_payload=svn_result,
            safe=self.safe,
            log=self.log,
            update=self.update,
            task_running=self.task_running,
            task_success=self.task_success,
            task_skipped=self.task_skipped,
            set_partial=self.set_partial,
            save_category_rows=self.save_category_rows,
            download_url=self.download_url,
            build_task_meta=self.build_task_meta,
            build_svn_section=self.build_svn_section,
            build_changes=self.build_changes,
            build_conflicts=self.build_conflicts,
            build_lineage_summary=_build_lineage_summary_payload,
            build_config_files=self.build_config_files,
            build_job_table=self.build_job_table,
            build_ai=self.build_ai,
            get_active_profile_name=self.get_active_profile_name,
            collect_hcyt_input_files=collect_hcyt_input_files,
            build_source_classified_progress=build_source_classified_progress,
            publish_hcyt_progress=publish_hcyt_progress,
            run_hcyt_rules=run_hcyt_rules,
            run_hcyt_inspections=run_hcyt_inspections,
            run_hcyt_ai_review=run_hcyt_ai_review,
            sync_hcyt_legacy_results=sync_hcyt_legacy_results,
            build_hcyt_report=build_hcyt_report,
            run_hcyt_schedule=self.run_hcyt_schedule,
            run_hcyt_programs=self.run_hcyt_programs,
            text_to_rows=text_to_rows,
            status_of=self.status_of,
            count_levels=self.count_levels,
        )

    def run(self):
        try:
            _load_real_modules()
            if _mods is None:
                self.log("真实审查引擎加载失败", "ERR")
                self.log(_import_error or "未知错误", "ERR", detail=True)
                failure = build_engine_load_failure_result(_import_error)
                self.finish(failure["status"], error=failure["error"])
                return

            workflow = resolve_workflow(self.repo, self.workflow)
            self.workflow = workflow
            source_label = build_source_label(self.repo, self.source_type)
            self.log(f"开始处理：{source_label}（工作流 {workflow}，来源 {self.source_type}）")
            self.task_running("source_load")
            self.update(progress=5, step=build_source_load_step(self.source_type))

            if self.source_type == "local":
                svn_result = resolve_workspace(
                    self.repo,
                    workflow,
                    self.source_type,
                    svn_loader=lambda source_ref: _mods.svn_main(workflow, source_ref),
                    local_loader=_mods.load_local_workspace,
                )
                self.log(f"本地目录加载完成，识别 {len(svn_result['exported_paths'])} 个待审计文件")
            else:
                svn_result = resolve_workspace(
                    self.repo,
                    workflow,
                    self.source_type,
                    svn_loader=lambda source_ref: _mods.svn_main(workflow, source_ref),
                    local_loader=lambda _source_ref, _workflow: None,
                )
                self.log(f"SVN 拉取完成，导出 {len(svn_result['exported_paths'])} 个变更文件")
            self.task_success("source_load", summary={"files": len(svn_result.get("exported_paths", []))})
            self._configure_source_downloads(svn_result)
            self.update(progress=25, step="分析文件")

            report = run_workflow(
                WorkflowRunContext(
                    workflow=workflow,
                    runtime_context=self.build_workflow_runtime(svn_result),
                )
            )

            report = finalize_run_result(
                report,
                svn_result=svn_result,
                source_ref=self.repo,
                fallback_source_type=self.source_type,
                logs=self.logs,
                build_source_summary=build_source_summary,
            )
            self.update(progress=100, step="完成")
            self.log("任务完成")
            self.finish(report["task"]["status"], report=report)
        except Exception as exc:
            if getattr(self, "_atomic_completion_failed", False):
                # The atomic repository already rolled back. Do not re-enter
                # finish() through the legacy persistence path.
                raise
            failure = build_failure_result(exc, source_type=self.source_type)
            message = failure["error"]
            self.log(f"任务异常: {message}", "ERR")
            self.log(traceback.format_exc(), "ERR", detail=True)
            self.finish(failure["status"], error=message)

    # ---- 公共构建 ----

    def download_url(self, path):
        relative_path = getattr(self, "_source_download_paths", {}).get(str(Path(path).resolve()))
        if not relative_path:
            return ""
        return build_source_download_url(self.task_id, relative_path)

    def build_task_meta(self, svn_result, status, extra):
        return _build_task_meta(
            svn_result=svn_result,
            status=status,
            extra=extra,
            repo=self.repo,
            workflow=self.workflow,
            workflow_names=WORKFLOW_NAMES,
            author=self.author,
            start_ts=self.start_ts,
            source_type=self.source_type,
        )

    def build_svn_section(self, svn_result):
        """SVN 变更文件清单 + trunk 重叠（Streamlit 顶部那个折叠区）。"""
        return {
            "branchChanged": svn_result.get("branch_changed_files", []),
            "trunkConflict": svn_result.get("trunk_conflict_files", []),
        }

    def build_changes(self, svn_result, path_map=None):
        paths = dict(path_map or {})
        paths.update(getattr(self, "_source_download_by_relative", {}))
        return _build_changes(svn_result, self.download_url, paths)

    def _configure_source_downloads(self, svn_result):
        if self.source_type == "local":
            root = svn_result.get("workspace_root") or self.repo
            self._source_download_paths = source_relative_paths(svn_result.get("exported_paths", []), root)
        else:
            self._source_download_paths = source_relative_paths_from_changes(
                svn_result.get("exported_paths", []), svn_result.get("branch_changed_files", [])
            )
        self._source_download_by_relative = {
            relative: path for path, relative in self._source_download_paths.items()
        }

    def build_conflicts(self, svn_result):
        return _build_conflicts(svn_result)

    @staticmethod
    def status_of(errors, warnings):
        return "fail" if errors else ("warn" if warnings else "pass")

    @staticmethod
    def count_levels(rows_groups):
        errors = sum(1 for rows in rows_groups for row in rows if row.get("level") == "err")
        warnings = sum(1 for rows in rows_groups for row in rows if row.get("level") == "warn")
        return errors, warnings

    def build_ai(self, targets, errors, warnings):
        return _build_ai(
            ai_enabled=self.ai_enabled,
            targets=targets,
            errors=errors,
            warnings=warnings,
            safe=self.safe,
            call_sql_llm=_mods.call_sql_llm,
        )

    @staticmethod
    def get_active_profile_name():
        return get_active_profile().name

    def load_result_table_annotations(self):
        return _load_result_table_annotations(
            safe=self.safe,
            public_data=_mods.public_data,
            normalize_table=normalize_table,
        )

    def annotate_table(self, name, disabled, sys_name_map):
        """返回 {name, disabled, sysNames, highlight}（highlight=禁用或重点源系统）。"""
        return _annotate_table(
            name,
            disabled,
            sys_name_map,
            normalize_table=normalize_table,
            highlight_result_source_systems=HIGHLIGHT_RESULT_SOURCE_SYSTEMS,
        )

    # ===================================================================
    # HCYT 工作流
    # ===================================================================

    def run_hcyt(self, svn_result):
        return _run_hcyt(self.build_workflow_runtime(svn_result))


    def build_config_files(self, config_paths):
        """schema_config ??JSON ?????????dict -> ???/???list[dict] -> ???????"""
        return _build_config_files(config_paths)

    def run_hcyt_schedule(self, plan_xls, seq_xls, cale_xls, job_xls, log_timing=None):
        """调度清单表格（PLAN/SEQ/CALE/JOB）+ 规则告警，复刻 hcyt_stream._render_schedule_section。"""
        return _run_hcyt_schedule(
            plan_xls,
            seq_xls,
            cale_xls,
            job_xls,
            safe=self.safe,
            modules=_mods,
            build_job_table=self.build_job_table,
            rule_label=rule_label,
            log_timing=log_timing,
        )

    def build_job_table(self, job_source, db_job_rows):
        """JOB ??4 ?????+ ??????new=????????/ disabled=??????????????
        ??? hcyt_stream.build_job_display_df ??????????"""
        return _build_job_table(job_source, db_job_rows)

    def run_hcyt_programs(self, py_lists, job_df, program_xls, db_job_rows, log_timing=None):
        return _run_hcyt_programs(
            py_lists,
            job_df,
            program_xls,
            db_job_rows,
            safe=self.safe,
            modules=_mods,
            download_url=self.download_url,
            load_result_table_annotations=self.load_result_table_annotations,
            annotate_table=self.annotate_table,
            profile_name=self.get_active_profile_name(),
            normalize_table=normalize_table,
            dedupe_tables=dedupe_tables,
            cale_map=CALE_MAP,
            text_to_rows=text_to_rows,
            log_timing=log_timing,
        )

    # ===================================================================
    # NUPS 工作流
    # ===================================================================

    def run_nups(self, svn_result):
        return _run_nups(self.build_workflow_runtime(svn_result))


    # ===================================================================
    # FineReport 工作流
    # ===================================================================

    def run_fine(self, svn_result):
        return _run_fine(self.build_workflow_runtime(svn_result))

def start_task(task_id, repo, workflow, ai_enabled=False, debug_enabled=False, author="local-user", source_type="svn"):
    run = TaskRun(task_id, repo, workflow, ai_enabled, debug_enabled, author, source_type)
    thread = threading.Thread(target=run.run, name=f"audit-task-{task_id}", daemon=True)
    thread.start()
    return thread
