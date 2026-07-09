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
    for path in (targets or [])[:10]:
        result = safe("AI 大模型", lambda p=path: call_sql_llm(p), None)
        if result:
            findings.append({"sev": "info", "title": Path(path).name, "body": str(result)})
    verdict = "err" if errors else ("warn" if warnings else "ok")
    summary = f"静态规则共发现 {errors} 个错误、{warnings} 个警告。"
    summary += "建议修复后再合并。" if errors else "整体符合规范。"
    return {
        "model": "行内大模型（svn_check ai_service）",
        "verdict": verdict,
        "summary": summary,
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


def build_job_table(job_source, db_job_rows):
    display = job_source.iloc[:, :4].fillna("")
    display.columns = ["计划名", "作业流名", "作业名", "作业描述"]

    def norm(value):
        return "" if value is None else str(value).strip().upper()

    prod = {}
    for row in (db_job_rows or []):
        if len(row) > 23 and norm(row[2]):
            prod[norm(row[2])] = row

    row_states = []
    for _, row in display.iterrows():
        prod_row = prod.get(norm(row["作业名"]))
        if prod_row is None:
            row_states.append("new" if db_job_rows else "")
        elif str(prod_row[23]).strip() in ("9", "9.0"):
            row_states.append("disabled")
        else:
            row_states.append("")

    return {"columns": list(display.columns), "rows": display.astype(str).values.tolist()}, row_states
