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
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from .compat import (
    build_legacy_fine_audit_result_rows,
    build_legacy_nups_audit_result_rows,
)
from .hcyt_ai_review import run_hcyt_ai_review
from .hcyt_file_classifier import collect_hcyt_input_files
from .hcyt_inspection_orchestrator import run_hcyt_inspections
from .hcyt_progress_events import build_source_classified_progress, publish_hcyt_progress
from .hcyt_report_builder import build_hcyt_report
from .hcyt_legacy_result_sync import sync_hcyt_legacy_results
from .lineage_payload import empty_lineage_summary, json_safe, lineage_warning
from .report_builder import (
    build_ai as _build_ai,
    build_changes as _build_changes,
    build_config_files as _build_config_files,
    build_conflicts as _build_conflicts,
    build_job_table as _build_job_table,
    build_task_meta as _build_task_meta,
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
from .workflow_dispatcher import WorkflowRunContext, run_workflow
from db.profiles import get_active_profile
from db.runtime_store import (
    persist_task_run_completion,
    replace_audit_results,
    update_task_runtime_state,
)

_empty_lineage_summary = empty_lineage_summary
_rule_label = rule_label

try:
    from .run import AuditRunState, AuditTask, AuditTaskStatus
except ImportError:  # pragma: no cover - direct module execution fallback
    from run import AuditRunState, AuditTask, AuditTaskStatus

# 把拷贝进来的真实项目加入模块搜索路径，保持其内部 `from core...`、
# `from services...`、`from shared...` 等绝对导入原样可用。
SVN_CHECK_DIR = Path(__file__).resolve().parents[1] / "svn_check"
if str(SVN_CHECK_DIR) not in sys.path:
    sys.path.insert(0, str(SVN_CHECK_DIR))

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

            from services.svn_service import svn_main
            from services.ai_service import call_sql_llm
            from services import re_service
            from services import audit_metadata_service
            from services.workspace_service import load_local_workspace
            import core.hcyt as hcyt
            import core.nups_rule as nups_rule
            import core.fine_rule as fine_rule
            import core.public_data as public_data
            from core.asset_issue import asset_issues_to_unified_issues, dedupe_issues
            from core.hcyt import ddl_rule as hcyt_ddl_rule
            from core.hcyt import python_rule as hcyt_python_rule
            from core.hcyt import sql_rule as hcyt_sql_rule
            from shared.lineage.mapping_sqlite import load_registered_result_tables

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


def _build_lineage_summary_payload(m, job_df=None, program_xls=None, py_lists=None, db_job_rows=None):
    warnings = []
    merge_df = None
    job_outfile_lookup = {}
    metadata_service = getattr(m, "audit_metadata_service", None)

    if metadata_service is None:
        warnings.append("job metadata unavailable")
    else:
        try:
            job_outfile_rows = metadata_service.list_job_outfiles() or []
            job_outfile_lookup = m.re_service.build_job_outfile_lookup(job_outfile_rows)
        except Exception as exc:
            warnings.append(lineage_warning("job outfile metadata", exc))
            job_outfile_lookup = {}

    if job_df is not None and program_xls:
        try:
            program_df = m.re_service.load_xls_to_df(program_xls)
            merge_job = m.hcyt.all_job_df(job_df, db_job_rows) if db_job_rows is not None else job_df
            try:
                merge_program = m.hcyt.all_program_df(program_df)
            except Exception:
                merge_program = program_df
            merge_df = m.re_service.merge_job_program(merge_job, merge_program)
        except Exception as exc:
            warnings.append(lineage_warning("merge metadata", exc))
    elif job_df is None:
        warnings.append("job metadata unavailable")

    try:
        summary = m.re_service.build_wide_table_lineage_summary(
            merge_df=merge_df,
            input_path=None,
            job_outfile_lookup=job_outfile_lookup,
            metadata_service=metadata_service,
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

    # ---- 日志 / 进度 ----

    def _ensure_run_state(self):
        if not hasattr(self, "run_state"):
            self.run_state = create_audit_run_state(self.task_id, self.workflow)
            self.run_state.mark_running()
        return self.run_state

    def log(self, msg, level="INFO"):
        entry = {"ts": datetime.now().strftime("%H:%M:%S"), "level": level, "msg": str(msg)}
        self.logs.append(entry)
        self._ensure_run_state().add_log(str(msg), level=level)
        print(f"[task {self.task_id}] {level} {msg}", flush=True)

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

    def run(self):
        try:
            _load_real_modules()
            if _mods is None:
                self.log("真实审查引擎加载失败", "ERR")
                self.log(_import_error or "未知错误", "ERR")
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
            self.update(progress=25, step="分析文件")

            report = run_workflow(
                WorkflowRunContext(
                    workflow=workflow,
                    svn_result=svn_result,
                    run_hcyt=self.run_hcyt,
                    run_nups=self.run_nups,
                    run_fine=self.run_fine,
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
            failure = build_failure_result(exc, source_type=self.source_type)
            message = failure["error"]
            self.log(f"任务异常: {message}", "ERR")
            self.log(traceback.format_exc(), "ERR")
            self.finish(failure["status"], error=message)

    # ---- 公共构建 ----

    def download_url(self, path):
        return self.safe("下载链接", lambda: _mods.re_service.build_export_download_url(path), "") or ""

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
        return _build_changes(svn_result, self.download_url, path_map)

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

    def load_result_table_annotations(self):
        m = _mods
        disabled = set(self.safe(
            "禁用结果表(all_disabled_result_tables)",
            lambda: {normalize_table(r[0]) for r in (m.public_data.all_disabled_result_tables() or []) if r and r[0]},
            set(),
        ))
        sys_name_map = {}

        def build_sys_map():
            mapping = {}
            for row in (m.public_data.all_result_table_sys_names() or []):
                if not row or len(row) < 2 or row[0] is None or row[1] is None:
                    continue
                table = normalize_table(row[0])
                sys_name = str(row[1]).strip()
                if table and sys_name:
                    mapping.setdefault(table, [])
                    if sys_name not in mapping[table]:
                        mapping[table].append(sys_name)
            return mapping

        sys_name_map = self.safe("结果表源系统(all_result_table_sys_names)", build_sys_map, {})
        return disabled, sys_name_map

    def annotate_table(self, name, disabled, sys_name_map):
        """返回 {name, disabled, sysNames, highlight}（highlight=禁用或重点源系统）。"""
        normalized = normalize_table(name)
        sys_names = sys_name_map.get(normalized, [])
        is_disabled = normalized in disabled
        highlight = is_disabled or any(
            s.strip().upper() in {h.upper() for h in HIGHLIGHT_RESULT_SOURCE_SYSTEMS} for s in sys_names)
        return {"name": normalized, "disabled": is_disabled, "sysNames": sys_names, "highlight": highlight}

    # ===================================================================
    # HCYT 工作流
    # ===================================================================

    def run_hcyt(self, svn_result):
        m = _mods
        self.task_running("classify_files")
        input_files = collect_hcyt_input_files(
            svn_result=svn_result,
            re_service=m.re_service,
            hcyt=m.hcyt,
            build_changes=self.build_changes,
            build_conflicts=self.build_conflicts,
        )
        (dws_url, hive_url, schame_config_lists, sbin_lists, recv_lists, dwo_lists, dwf_lists,
         py_lists, plan_xls, seq_xls, job_xls, program_xls, cale_xls, grouped, changes, conflicts
         ) = input_files.as_run_inputs()
        publish_hcyt_progress(self.set_partial, build_source_classified_progress(changes=changes, conflicts=conflicts))
        self.task_success("classify_files", summary={"changedFiles": len(changes)})
        self.task_success("trunk_conflicts", result=conflicts, summary={"conflicts": len(conflicts)})

        # --- SQL / 脚本 / 配置类规则 ---
        self.update(progress=35, step="SQL 与配置规则检查")
        sql_checks = {}
        asset_issues = []
        if dws_url:
            self.task_running("dws_sql")
            result = self.safe("dws.sql 规则", lambda: m.hcyt.rule_dws(dws_url), ("", "", 0))
            grouped["dws"] += text_to_rows(result[0], result[1], m.re_service.get_filename(dws_url), warn_level="info")
            sql_checks["dws"] = {"script": m.re_service.get_filename(dws_url), "downloadUrl": self.download_url(dws_url)}
            dws_file_name = m.re_service.get_filename(dws_url)
            dws_sql_text = self.safe("dws.sql 内容读取", lambda: m.re_service.read_data_from_file(dws_url), "")
            asset_issues += self.safe(
                "dws.sql 词根结构化 issue",
                lambda: m.hcyt_ddl_rule.collect_root_missing_issues(dws_sql_text, "hcyt", dws_file_name),
                [],
            )
            asset_issues += self.safe(
                "dws.sql 资产表待核对 issue",
                lambda: m.hcyt_sql_rule.collect_created_table_review_issues(dws_url, "hcyt", dws_file_name),
                [],
            )
            self.set_partial("dws", grouped["dws"])
            self.task_success("dws_sql", result=grouped["dws"], summary={"issues": len(grouped["dws"])})
        else:
            self.task_skipped("dws_sql", "no dws.sql file")
        if hive_url:
            self.task_running("hive_sql")
            result = self.safe("hive.sql 规则", lambda: m.hcyt.rule_hive(hive_url), ("", "", 0))
            grouped["hive"] += text_to_rows(result[0], result[1], m.re_service.get_filename(hive_url), warn_level="info")
            sql_checks["hive"] = {"script": m.re_service.get_filename(hive_url), "downloadUrl": self.download_url(hive_url)}
            self.set_partial("hive", grouped["hive"])
            self.task_success("hive_sql", result=grouped["hive"], summary={"issues": len(grouped["hive"])})
        else:
            self.task_skipped("hive_sql", "no hive.sql file")
        if sbin_lists:
            self.task_running("post_scripts")
            result = self.safe("sbin 规则", lambda: m.hcyt.rule_sbin(sbin_lists), ("", "", 0))
            grouped["sbin"] += text_to_rows(result[0], result[1], "sbin")
            self.set_partial("sbin", grouped["sbin"])
            self.task_success("post_scripts", result=grouped["sbin"], summary={"issues": len(grouped["sbin"])})
        else:
            self.task_skipped("post_scripts", "no post script files")
        if recv_lists:
            self.task_running("recv_config")
            result = self.safe("recv 卸数规则", lambda: m.hcyt.rule_recv_json(recv_lists), ("", "", 0))
            grouped["recv"] += text_to_rows(result[0], result[1], "recv_json")
            self.set_partial("recv", grouped["recv"])
            self.task_success("recv_config", result=grouped["recv"], summary={"issues": len(grouped["recv"])})
        else:
            self.task_skipped("recv_config", "no recv config files")

        # schema_config：规则告警 + JSON 表格化（Streamlit render_schema_config_tables）
        config_files = []
        if schame_config_lists:
            self.task_running("config_files")
            result = self.safe("schema_config 规则", lambda: m.hcyt.rule_config(schame_config_lists), ("", "", 0))
            grouped["config"] += text_to_rows(result[0], result[1], "SCHEMA_CONFIG", err_level="warn")
            config_files = self.build_config_files(schame_config_lists)
            self.set_partial("config", grouped["config"])
            self.set_partial("configFiles", config_files)
            self.task_success("config_files", result=grouped["config"], summary={"issues": len(grouped["config"])})
        else:
            self.task_skipped("config_files", "no schema config files")

        # dwo / dwf
        for path in dwo_lists or []:
            result = self.safe("dwo 规则", lambda p=path: m.hcyt.rule_dwo(p), ("", "", 0))
            grouped["python"] += text_to_rows(result[0], result[1], m.re_service.get_filename(path))
        for path in dwf_lists or []:
            result = self.safe("dwf 规则", lambda p=path: m.hcyt.rule_dwf(p), ("", "", 0))
            grouped["python"] += text_to_rows(result[0], result[1], m.re_service.get_filename(path))

        # --- 调度 Excel：清单表格 + 规则 ---
        self.update(progress=50, step="调度规范检查")
        self.task_running("schedule")
        inspections = run_hcyt_inspections(
            plan_xls=plan_xls,
            seq_xls=seq_xls,
            cale_xls=cale_xls,
            job_xls=job_xls,
            py_lists=py_lists,
            program_xls=program_xls,
            task_id=self.task_id,
            initial_asset_issues=asset_issues,
            run_schedule=self.run_hcyt_schedule,
            run_programs=self.run_hcyt_programs,
            build_lineage_summary=_build_lineage_summary_payload,
            modules=m,
            log_schedule_warning=lambda msg: self.log(msg, "WARN"),
            update_progress=self.update,
            task_running=self.task_running,
            task_success=self.task_success,
            set_partial=self.set_partial,
            grouped=grouped,
        )
        schedule = inspections.schedule
        py_scripts = inspections.py_scripts
        ref_tables = inspections.ref_tables
        deps = inspections.deps
        asset_issues = inspections.asset_issues
        unified_asset_issues = inspections.unified_asset_issues
        lineage_summary = inspections.lineage_summary

        errors, warnings = self.count_levels(list(grouped.values()) + [schedule["rows"]])
        ai = run_hcyt_ai_review(
            py_lists=py_lists,
            dws_url=dws_url,
            errors=errors,
            warnings=warnings,
            ai_enabled=self.ai_enabled,
            update_progress=self.update,
            build_ai=self.build_ai,
        )

        status = self.status_of(errors + len(conflicts), warnings)
        checks = sum(1 for flag in (dws_url, hive_url, sbin_lists, schame_config_lists, recv_lists,
                                    dwo_lists or dwf_lists, plan_xls, seq_xls, job_xls, py_lists) if flag)

        sync_hcyt_legacy_results(self.save_category_rows, grouped)
        report = build_hcyt_report(
            task=self.build_task_meta(svn_result, status, {
                "changedFiles": len(changes), "checks": checks, "errors": errors,
                "warnings": warnings, "conflicts": len(conflicts),
                "sqlFiles": len(svn_result["exported_paths"]),
            }),
            svn=self.build_svn_section(svn_result),
            changes=changes,
            conflicts=conflicts,
            grouped=grouped,
            sql_checks=sql_checks,
            config_files=config_files,
            schedule=schedule,
            py_scripts=py_scripts,
            ref_tables=ref_tables,
            deps=deps,
            asset_issues=asset_issues,
            unified_asset_issues=unified_asset_issues,
            lineage_summary=lineage_summary,
            ai=ai,
        )
        return report

    def build_config_files(self, config_paths):
        """schema_config ??JSON ?????????dict -> ???/???list[dict] -> ???????"""
        return _build_config_files(config_paths)

    def run_hcyt_schedule(self, plan_xls, seq_xls, cale_xls, job_xls):
        """调度清单表格（PLAN/SEQ/CALE/JOB）+ 规则告警，复刻 hcyt_stream._render_schedule_section。"""
        m = _mods
        rows = []
        tables = {}
        summary = {"plan": 0, "seq": 0, "job": 0, "cycles": 0, "missing": 0}
        job_df = r_plan = db_job_rows = None

        def df_table(df, columns=None):
            display = df.fillna("") if df is not None else None
            if display is None:
                return {"columns": [], "rows": []}
            cols = columns or [str(c) for c in display.columns]
            return {"columns": cols, "rows": display.astype(str).values.tolist()}

        if plan_xls:
            plan_source = self.safe("PLAN Excel", lambda: m.re_service.load_xls_to_df(plan_xls), None)
            if plan_source is not None:
                summary["plan"] = len(plan_source)
                plan_df = plan_source.iloc[:, [0, 4]].fillna("")
                plan_df.columns = ["计划名", "前置依赖"]
                tables["plan"] = {"title": "PLAN 计划清单", **df_table(plan_df)}
                result = self.safe("PLAN 规则", lambda: m.hcyt.rule_excle_plan(plan_df), ("", "", 0, None))
                r_plan = result[3] if len(result) > 3 else None
                plan_rows = self._schedule_rows(result[0], result[1])
                tables["plan"]["messages"] = plan_rows
                rows += [{"table": "PLAN", "item": Path(plan_xls).name, **r} for r in plan_rows]

        if seq_xls:
            seq_source = self.safe("SEQ Excel", lambda: m.re_service.load_xls_to_df(seq_xls), None)
            if seq_source is not None:
                summary["seq"] = len(seq_source)
                seq_df = seq_source.iloc[:, [0, 1, 2]].fillna("")
                seq_df.columns = ["计划名", "作业流名", "作业流描述"]
                tables["seq"] = {"title": "SEQ 作业流清单", **df_table(seq_df)}
                result = self.safe("SEQ 规则", lambda: m.hcyt.rule_excle_seq(seq_df), ("", "", 0))
                seq_rows = self._schedule_rows(result[0], result[1])
                tables["seq"]["messages"] = seq_rows
                rows += [{"table": "SEQ", "item": Path(seq_xls).name, **r} for r in seq_rows]

        if cale_xls:
            cale_source = self.safe("CALE Excel", lambda: m.re_service.load_xls_to_df(cale_xls), None)
            if cale_source is not None:
                tables["cale"] = {"title": "CALE 日历清单", **df_table(cale_source)}

        if job_xls:
            job_source = self.safe("JOB Excel", lambda: m.re_service.load_xls_to_df(job_xls), None)
            if job_source is not None:
                summary["job"] = len(job_source)
                job_df = job_source
                db_job_rows = self.safe("线上作业查询(all_job)", m.public_data.all_job, None)
                job_table, row_states = self.build_job_table(job_source, db_job_rows)
                tables["job"] = {"title": "JOB 作业清单（绿=新增 / 红=禁用再上线）",
                                 "rowStates": row_states, **job_table}
                result = self.safe(
                    "JOB 规则",
                    lambda: m.hcyt.rule_excle_job(job_df, r_plan=r_plan, timing_log=None, job_rows=db_job_rows),
                    ("", "", 0))
                job_rows = self._schedule_rows(result[0], result[1])
                tables["job"]["messages"] = job_rows
                rows += [{"table": "JOB", "item": Path(job_xls).name, **r} for r in job_rows]
                summary["cycles"] = sum(1 for r in job_rows if "成环" in r["msg"] or "循环" in r["msg"])
                summary["missing"] = sum(1 for r in job_rows if ("不存在" in r["msg"] or "未在生产" in r["msg"]))

        return {"summary": summary, "rows": rows, "tables": tables,
                "_job_df": job_df, "_r_plan": r_plan, "_db_job_rows": db_job_rows}

    def build_job_table(self, job_source, db_job_rows):
        """JOB ??4 ?????+ ??????new=????????/ disabled=??????????????
        ??? hcyt_stream.build_job_display_df ??????????"""
        return _build_job_table(job_source, db_job_rows)

    @staticmethod
    def _schedule_rows(result_text, warn_text):
        rows = []
        for raw, level in ((result_text, "err"), (warn_text, "warn")):
            if not raw or not isinstance(raw, str):
                continue
            for line in raw.split("\n"):
                line = line.strip()
                if line:
                    rows.append({"rule": rule_label(line), "level": level, "msg": line})
        return rows

    def run_hcyt_programs(self, py_lists, job_df, program_xls, db_job_rows):
        m = _mods
        py_scripts, py_rows, ref_tables, deps, asset_issues = [], [], [], [], []
        if not py_lists:
            return py_scripts, py_rows, ref_tables, deps, asset_issues

        # 调度关联（JOB/PROGRAM Excel + 线上库）
        program_lookup = dependency_lookup = None
        if job_df is not None and program_xls:
            def build_lookups():
                program_df = m.re_service.load_xls_to_df(program_xls)
                merge_job = m.hcyt.all_job_df(job_df, db_job_rows) if db_job_rows is not None else job_df
                try:
                    merge_program = m.hcyt.all_program_df(program_df)
                except Exception:
                    merge_program = program_df
                prog_path_col = merge_program.columns[4]
                merged = m.re_service.merge_job_program(merge_job, merge_program)
                return (m.re_service.build_program_lookup(merged, prog_path_col, tail_levels=4),
                        m.re_service.build_dependency_table_lookup(merged))
            program_lookup, dependency_lookup = self.safe("JOB/PROGRAM 调度关联", build_lookups, (None, None))

        registered = set(self.safe(
            "结果表登记库(lineage)",
            lambda: m.load_registered_result_tables(profile=get_active_profile().name),
            set(),
        ))
        para_tables = set(self.safe(
            "码值参数表(all_para_table_lists)",
            lambda: {normalize_table(r[0]) for r in m.public_data.all_para_table_lists() if r and r[0]},
            set()))
        disabled, sys_name_map = self.load_result_table_annotations()
        disabled_job_names = set(self.safe(
            "禁用作业(all_job)",
            lambda: {str(r[2]).strip().upper() for r in (db_job_rows or m.public_data.all_job() or [])
                     if len(r) > 23 and r[2] and str(r[23]).strip() in ("9", "9.0")},
            set()))

        upstream_tables, job_names = [], []
        for path in py_lists:
            file_name = m.re_service.get_filename(path)
            result = self.safe(f"加工程序规则({file_name})", lambda p=path: m.hcyt.rule_dws_py(p), ("", "", 0, []))
            lint = text_to_rows(result[0], result[1], file_name)
            sql_tables = dedupe_tables(result[3] if len(result) > 3 else [])
            table_name = self.safe("表名解析", lambda p=path: m.hcyt.get_program_table_name(p), "")
            source_text = self.safe(f"加工程序内容读取({file_name})", lambda p=path: m.re_service.read_data_from_file(p), "")
            asset_issues += self.safe(
                f"加工程序资产表待核对 issue({file_name})",
                lambda names=sql_tables, source=file_name: m.hcyt_python_rule.build_asset_table_review_issues(
                    names, "hcyt", source
                ),
                [],
            )
            asset_issues += self.safe(
                f"加工程序词根结构化 issue({file_name})",
                lambda text=source_text, source=file_name: m.hcyt_ddl_rule.collect_root_missing_issues(
                    text, "hcyt", source
                ),
                [],
            )

            job_name, freq, yilai_tables = "", "", None
            if program_lookup is not None:
                def lookup(p=path):
                    info = m.re_service.get_program_lookup_result(
                        program_lookup, m.re_service.safe_remove_prefix(p), tail_levels=4)
                    yilai = m.re_service.get_yilai_table_from_lookup(info[2], dependency_lookup)
                    return info[0], info[1], yilai
                looked = self.safe(f"调度信息关联({file_name})", lookup, ("", "", None))
                job_name = str(looked[0] or "")
                freq = CALE_MAP.get(looked[1], str(looked[1] or ""))
                yilai_tables = dedupe_tables(looked[2]) if looked[2] is not None else None

            current_result_tables = registered | ({normalize_table(table_name)} if table_name else set())
            result_tables = [t for t in sql_tables if t in current_result_tables]
            code_tables = [t for t in sql_tables if t in para_tables]
            middle_tables = [t for t in sql_tables if t not in current_result_tables and t not in para_tables]

            compare_rows = []
            if yilai_tables is not None:
                left, right = set(result_tables), set(yilai_tables)
                for name in sorted(left & right):
                    ann = self.annotate_table(name, disabled, sys_name_map)
                    compare_rows.append({"sql": name, "dep": name, "state": "same", **ann})
                for name in sorted(left - right):
                    ann = self.annotate_table(name, disabled, sys_name_map)
                    compare_rows.append({"sql": name, "dep": None, "state": "missing", **ann})
                for name in sorted(right - left):
                    compare_rows.append({"sql": None, "dep": name, "state": "extra",
                                         "name": name, "disabled": False, "sysNames": [], "highlight": False})
                upstream_tables += yilai_tables
                focus = "重点检查 SQL 结果表依赖与调度依赖是否一致。"
            else:
                focus = "调度依赖比对不可用（行内库/调度Excel缺失），请人工核对结果表依赖。"

            if job_name:
                job_names.append(job_name)
            py_rows += lint
            py_scripts.append({
                "script": file_name,
                "downloadUrl": self.download_url(path),
                "table": table_name,
                "job": job_name,
                "jobDisabled": normalize_table(job_name) in disabled_job_names if job_name else False,
                "freq": freq,
                "focus": focus,
                "lint": lint,
                "result": compare_rows,
                "codeval": code_tables,
                "temp": middle_tables,
            })

            seen = {item["name"] for item in ref_tables}
            for names, ttype in ((result_tables, "result"), (code_tables, "src"), (middle_tables, "mid")):
                for name in names:
                    if name not in seen:
                        ref_tables.append({"name": name, "type": ttype})
                        seen.add(name)

        upstream_tables = dedupe_tables(upstream_tables)[:16]
        if upstream_tables or job_names:
            deps = [
                {"lane": "上游 / 调度依赖表", "nodes": [{"name": n, "q": ""} for n in upstream_tables]},
                {"lane": "本次作业", "nodes": [{"name": n, "q": "", "focus": True} for n in sorted(set(job_names))]},
            ]
        return py_scripts, py_rows, ref_tables, deps, asset_issues

    # ===================================================================
    # NUPS 工作流
    # ===================================================================

    def run_nups(self, svn_result):
        m = _mods
        exported = svn_result["exported_paths"]
        sql_lists, py_lists = m.nups_rule.get_nups_type(exported)

        self.update(progress=45, step="NUPS SQL 检查")
        sql_checks = []
        for path in sql_lists or []:
            result = self.safe("NUPS SQL 规则", lambda p=path: m.nups_rule.rule_dws(p), ("", 0))
            sql_checks.append({
                "script": m.re_service.get_filename(path),
                "downloadUrl": self.download_url(path),
                "messages": text_to_messages(result[0], ""),
            })

        self.update(progress=65, step="NUPS 加工程序检查")
        py_scripts = []
        for path in py_lists or []:
            file_name = m.re_service.get_filename(path)
            result = self.safe(f"NUPS 加工程序规则({file_name})", lambda p=path: m.nups_rule.rule_dws_py(p), ("", 0, []))
            sql_tables = dedupe_tables(result[2] if len(result) > 2 else [])
            table_name = self.safe("表名解析", lambda p=path: m.nups_rule.get_program_table_name(p), "")
            py_scripts.append({
                "script": file_name,
                "downloadUrl": self.download_url(path),
                "path": m.re_service.safe_remove_prefix(path),
                "table": table_name,
                "messages": text_to_messages(result[0], ""),
                "sqlRefs": sql_tables,
            })

        all_rows = [{"level": msg["level"], "msg": msg["msg"]} for c in sql_checks for msg in c["messages"]]
        all_rows += [{"level": msg["level"], "msg": msg["msg"]} for s in py_scripts for msg in s["messages"]]
        errors = sum(1 for r in all_rows if r["level"] == "err")
        warnings = sum(1 for r in all_rows if r["level"] == "warn")
        ai = self.build_ai(py_lists or sql_lists or [], errors, warnings)
        conflicts = self.build_conflicts(svn_result)
        status = self.status_of(errors + len(conflicts), warnings)

        # 旧接口 audit_results 也写一份
        self.save_category_rows(build_legacy_nups_audit_result_rows(sql_checks, rule_label))

        report = {
            "task": self.build_task_meta(svn_result, status, {
                "changedFiles": len(svn_result.get("branch_changed_files", [])),
                "checks": len(sql_lists or []) + len(py_lists or []),
                "errors": errors, "warnings": warnings, "conflicts": len(conflicts),
            }),
            "svn": self.build_svn_section(svn_result),
            "changes": self.build_changes(svn_result),
            "conflicts": conflicts,
            "sqlChecks": sql_checks,
            "pyScripts": py_scripts,
            "assetIssues": [],
            "unifiedAssetIssues": [],
        }
        if ai:
            report["ai"] = ai
        return report

    # ===================================================================
    # FineReport 工作流
    # ===================================================================

    def run_fine(self, svn_result):
        m = _mods
        exported = svn_result["exported_paths"]
        from urllib.parse import quote

        cpt_lists, menu_url, authority_url = [], "", ""
        for path in exported:
            if path.endswith((".frm", ".cpt")):
                cpt_lists.append(path)
            elif "menu.txt" in path:
                menu_url = path
            elif "authority.txt" in path:
                authority_url = path

        # --- 目录 / 权限（表格 + 规则）---
        self.update(progress=40, step="目录与权限检查")
        menu_section = authority_section = None
        menu_lists = []
        if menu_url:
            table = self.safe(
                "目录表(menu.txt)",
                lambda: m.re_service.load_txt_to_df(menu_url, ["后台目录", "前台目录", "预览方式"]),
                None)
            result = self.safe("目录规则(rule_menu)", lambda: m.fine_rule.rule_menu(menu_url), ([], "", 0))
            menu_lists = result[0] if isinstance(result, tuple) and result else []
            menu_section = {
                "columns": ["后台目录", "前台目录", "预览方式"],
                "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
                "messages": text_to_messages(result[1] if isinstance(result, tuple) and len(result) > 1 else "", ""),
            }
        if authority_url:
            table = self.safe(
                "权限表(authority.txt)",
                lambda: m.re_service.load_txt_to_df2(authority_url, ["前台目录", "赋予权限"]),
                None)
            result = self.safe("权限规则(rule_authority)",
                               lambda: m.fine_rule.rule_authority(authority_url, menu_lists), ("", 0))
            text = result[0] if isinstance(result, tuple) else str(result)
            authority_section = {
                "columns": ["前台目录", "赋予权限"],
                "rows": table.fillna("").astype(str).values.tolist() if table is not None else [],
                "messages": text_to_messages(text, ""),
            }

        # --- 报表模板 ---
        self.update(progress=55, step="帆软模板检查")
        registered = set(self.safe(
            "结果表登记库(lineage)",
            lambda: m.load_registered_result_tables(profile=get_active_profile().name),
            set(),
        ))
        para_tables = set(self.safe(
            "码值参数表(all_para_table_lists)",
            lambda: {normalize_table(r[0]) for r in m.public_data.all_para_table_lists() if r and r[0]},
            set()))
        disabled, sys_name_map = self.load_result_table_annotations()

        reports, all_ref_tables = [], []
        for path in cpt_lists:
            file_name = m.re_service.get_filename(path)
            result = self.safe(f"帆软规则({file_name})", lambda p=path: m.fine_rule.rule_fine(p), None)
            issues, ref_tables = [], []
            title, conn, engine_flag, sheets, datasets = file_name, "-", "", [], []
            viewlet = ""
            if isinstance(result, tuple) and len(result) >= 3:
                text, _cnt, detail = result[0], result[1], result[2]
                issues = [{"cat": "dataset", "loc": file_name, "rule": rule_label(line), "level": "err", "msg": line}
                          for line in str(text or "").split("\n") if line.strip() and line.strip() != "存在问题:"]
                viewlet = str(detail[0]) if detail and detail[0] else ""
                title = viewlet or file_name
                conn = str(detail[1]) if len(detail) > 1 and detail[1] else "-"
                engine_flag = str(detail[2]) if len(detail) > 2 else ""
                sheets = list(detail[3]) if len(detail) > 3 and detail[3] else []
                sql_tables = dedupe_tables(detail[4] if len(detail) > 4 else [])
                sql_text = self.safe("数据集 SQL 提取", lambda p=path: m.fine_rule.get_cpt_sql(p), "")
                if sql_text:
                    datasets = [{"name": "数据集 SQL", "sql": (sql_text or "").strip(), "rows": "-"}]
                for name in sql_tables:
                    ttype = "result" if name in registered else ("src" if name in para_tables else "mid")
                    ann = self.annotate_table(name, disabled, sys_name_map)
                    ref_tables.append({"name": name, "type": ttype, **ann})
            elif result is not None:
                issues = [{"cat": "tpl", "loc": file_name, "rule": "规则执行异常", "level": "warn", "msg": str(result)}]

            preview_url = (f"https://fine.example.com/svn_check.html?viewlet={quote(viewlet, safe='')}"
                           if viewlet else "")
            reports.append({
                "title": title,
                "file": m.re_service.safe_remove_prefix(path),
                "type": "frm" if path.endswith(".frm") else "cpt",
                "change": "M",
                "conn": conn,
                "engine": engine_flag,
                "sheets": sheets,
                "previewUrl": preview_url,
                "downloadUrl": self.download_url(path),
                "focus": "重点检查数据集 SQL、数据连接、敏感字段与权限。",
                "datasets": datasets,
                "issues": issues,
                "refTables": ref_tables,
            })
            seen = {item["name"] for item in all_ref_tables}
            for item in ref_tables:
                if item["name"] not in seen:
                    all_ref_tables.append(item)
                    seen.add(item["name"])

        admin_issue_count = 0
        for section in (menu_section, authority_section):
            if section:
                admin_issue_count += len(section["messages"])
        errors = sum(1 for r in reports for i in r["issues"] if i["level"] == "err")
        errors += sum(1 for s in (menu_section, authority_section) if s for msg in s["messages"] if msg["level"] == "err")
        warnings = sum(1 for r in reports for i in r["issues"] if i["level"] == "warn")
        warnings += sum(1 for s in (menu_section, authority_section) if s for msg in s["messages"] if msg["level"] == "warn")
        ai = self.build_ai(cpt_lists, errors, warnings)
        status = self.status_of(errors, warnings)

        self.save_category_rows(build_legacy_fine_audit_result_rows(reports))

        report = {
            "task": self.build_task_meta(svn_result, status, {
                "reports": len(reports),
                "checks": len(cpt_lists) + (1 if menu_url else 0) + (1 if authority_url else 0),
                "errors": errors, "warnings": warnings,
            }),
            "svn": self.build_svn_section(svn_result),
            "menu": menu_section,
            "authority": authority_section,
            "reports": reports,
            "refTables": all_ref_tables,
            "assetIssues": [],
            "unifiedAssetIssues": [],
        }
        if ai:
            report["ai"] = ai
        return report


def start_task(task_id, repo, workflow, ai_enabled=False, debug_enabled=False, author="local-user", source_type="svn"):
    run = TaskRun(task_id, repo, workflow, ai_enabled, debug_enabled, author, source_type)
    thread = threading.Thread(target=run.run, name=f"audit-task-{task_id}", daemon=True)
    thread.start()
    return thread
