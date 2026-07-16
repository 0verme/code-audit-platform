from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from .result_normalizer import format_duration
from .source_resolver import classify_change


def build_task_meta(*, svn_result, status, extra, repo, workflow, workflow_names, author, start_ts, source_type):
    revision = svn_result.get("create_revision", "")
    meta = {
        "status": status,
        "repo": repo,
        "sourceRef": repo,
        "module": workflow,
        "workflow": workflow_names.get(workflow, workflow),
        "revision": f"r{revision}" if revision else "-",
        "author": author,
        "startedAt": datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "duration": format_duration(time.time() - start_ts),
        "sourceType": svn_result.get("source_type", source_type),
        "workspaceRoot": svn_result.get("workspace_root", ""),
    }
    meta.update(extra)
    return meta


def build_changes(svn_result, download_url, path_map=None):
    path_map = path_map or {}
    rows = []
    for path in svn_result.get("branch_changed_files", []):
        local = path_map.get(path)
        rows.append({
            "type": "M",
            "path": path,
            "cat": classify_change(path),
            "downloadUrl": download_url(local) if local else "",
        })
    return rows


def build_conflicts(svn_result):
    return [
        {
            "path": path,
            "trunkRev": "trunk@HEAD",
            "mineRev": f"r{svn_result.get('create_revision', '')}" if svn_result.get("create_revision") else "branch",
            "note": "分支与最新 trunk 都改了该文件，合并前请人工核对。",
        }
        for path in svn_result.get("trunk_conflict_files", [])
    ]


def build_ai(*, ai_enabled, targets, errors, warnings, safe, call_sql_llm):
    if not ai_enabled:
        return None
    findings = []
    summaries = []
    for path in (targets or [])[:10]:
        result = safe("AI 大模型", lambda p=path: call_sql_llm(p), None)
        if result:
            if isinstance(result, dict):
                summaries.append(str(result.get("summary") or ""))
                for finding in result.get("findings", []):
                    if isinstance(finding, dict):
                        finding_with_source = dict(finding)
                        finding_with_source["title"] = (
                            Path(path).name + " · " + str(finding.get("title", "AI finding"))
                        )
                        findings.append(finding_with_source)
            else:
                findings.append({"sev": "info", "title": Path(path).name, "body": str(result)})
    verdict = "err" if errors else ("warn" if warnings else "ok")
    summary = f"静态规则共发现 {errors} 个错误、{warnings} 个警告。"
    summary += "建议修复后再合并。" if errors else "整体符合规范。"
    return {
        "model": "本地 OpenAI 兼容大模型",
        "verdict": verdict,
        "summary": "；".join(s for s in summaries if s) or summary,
        "findings": findings,
    }


def build_config_files(config_paths):
    files = []
    for path in config_paths:
        name = Path(path).name
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            files.append({"name": name, "error": f"无法按 JSON 解析: {exc}", "columns": [], "rows": []})
            continue
        if isinstance(data, dict):
            files.append({
                "name": name,
                "columns": ["字段", "值"],
                "rows": [[k, "" if v is None else str(v)] for k, v in data.items()],
            })
        elif isinstance(data, list) and data and all(isinstance(i, dict) for i in data):
            columns = sorted({k for item in data for k in item.keys()})
            files.append({
                "name": name,
                "columns": columns,
                "rows": [["" if item.get(c) is None else str(item.get(c, "")) for c in columns] for item in data],
            })
        else:
            files.append({"name": name, "columns": ["结果"], "rows": [[json.dumps(data, ensure_ascii=False)]]})
    return files


def build_job_table(job_source, db_job_rows, timing_log=None):
    def timed(label, fn, **fields):
        started = time.perf_counter()
        if timing_log is not None:
            timing_log(label, "start", **fields)
        try:
            return fn()
        finally:
            if timing_log is not None:
                timing_log(
                    label,
                    "end",
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                    **fields,
                )

    def prepare_display():
        prepared = job_source.iloc[:, :4].fillna("")
        prepared.columns = ["计划名", "作业流名", "作业名", "作业描述"]
        return prepared

    display = timed("schedule.job.table.prepare_display", prepare_display, rows=len(job_source))

    def norm(value):
        return "" if value is None else str(value).strip().upper()

    def build_prod_lookup():
        lookup = {}
        for row in (db_job_rows or []):
            if len(row) > 23 and norm(row[2]):
                lookup[norm(row[2])] = row
        return lookup

    prod = timed(
        "schedule.job.table.build_prod_lookup",
        build_prod_lookup,
        rows=len(db_job_rows or []),
    )

    display_rows = timed(
        "schedule.job.table.serialize_rows",
        lambda: display.astype(str).values.tolist(),
        rows=len(display),
    )

    def classify_states():
        states = []
        for row in display_rows:
            prod_row = prod.get(norm(row[2]))
            if prod_row is None:
                states.append("new" if db_job_rows else "")
            elif str(prod_row[23]).strip() in ("9", "9.0"):
                states.append("disabled")
            else:
                states.append("")
        return states

    row_states = timed(
        "schedule.job.table.classify_states",
        classify_states,
        rows=len(display_rows),
    )

    return {"columns": list(display.columns), "rows": display_rows}, row_states
