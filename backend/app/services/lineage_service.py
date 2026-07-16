from __future__ import annotations

import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import quote

from app.db.metadata.compat import router as db_router
from app.db.profiles import get_metadata_profile
from app.modules.audit.lineage_overlay import build_lineage_overlay
from app.modules.lineage.identifiers import normalize_registered_table_name
from app.modules.metadata.services.metadata_model import column_name, table_name
from app.services import ServiceError
from app.services.audit_task_service import get_report_json, get_task


DIRECTIONS = {"upstream", "downstream", "both"}


def _text(value) -> str:
    return str(value or "").strip()


def _path(value) -> str:
    return _text(value).replace("\\", "/")


def _job_key(value) -> str:
    return _text(value).upper()


def _table_key(value) -> str:
    return normalize_registered_table_name(value)


def _task_id(job_name: str, program_path: str) -> str:
    if job_name:
        return f"task:job:{quote(_job_key(job_name), safe='')}"
    digest = hashlib.sha1(_path(program_path).casefold().encode("utf-8")).hexdigest()[:16]
    return f"task:program:{digest}"


def _table_id(table: str) -> str:
    normalized = _table_key(table)
    return f"table:{quote(normalized, safe='')}"


def _edge_id(source: str, target: str, kind: str) -> str:
    digest = hashlib.sha1(f"{source}|{target}|{kind}".encode("utf-8")).hexdigest()[:20]
    return f"edge:{digest}"


def _dependency_jobs(raw) -> list[str]:
    if raw is None:
        return []
    return [part[3:].strip() for part in str(raw).split("|") if part.startswith("33:") and part[3:].strip()]


def _bounded_int(value, *, default: int, minimum: int, maximum: int, name: str) -> int:
    if value in (None, ""):
        return default
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError(f"{name} must be an integer", status_code=422) from exc
    if result < minimum or result > maximum:
        raise ServiceError(f"{name} must be between {minimum} and {maximum}", status_code=422)
    return result


def _baseline_sql(profile: str) -> str:
    jobs = table_name("jobs", profile)
    programs = table_name("programs", profile)
    return f"""
SELECT j.{column_name('jobs', 'job_name', profile)} AS job_name,
       j.{column_name('jobs', 'program_key', profile)} AS program_key,
       j.{column_name('jobs', 'dependencies', profile)} AS dependencies,
       j.{column_name('jobs', 'status', profile)} AS status_code,
       p.e AS program_path,
       substr(p.{column_name('programs', 'result_table', profile)}, 5) AS result_table
FROM {jobs} j
INNER JOIN {programs} p
  ON j.{column_name('jobs', 'program_key', profile)} = p.{column_name('programs', 'program_key', profile)}
ORDER BY j.{column_name('jobs', 'job_name', profile)}, p.e
"""


def _row_value(row, index: int, *names):
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        for name in names:
            if name in mapping:
                return mapping[name]
    if isinstance(row, dict):
        for name in names:
            if name in row:
                return row[name]
    try:
        return row[index]
    except (TypeError, IndexError, KeyError):
        return None


def load_baseline_programs(profile: str) -> list[dict]:
    rows = db_router.select_sql_with_profile(profile, _baseline_sql(profile)) or []
    programs = []
    for row in rows:
        programs.append({
            "jobName": _text(_row_value(row, 0, "job_name")),
            "programKey": _text(_row_value(row, 1, "program_key")),
            "dependencyJobs": _dependency_jobs(_row_value(row, 2, "dependencies")),
            "disabled": _text(_row_value(row, 3, "status_code")) == "9",
            "programPath": _path(_row_value(row, 4, "program_path")),
            "resultTable": _table_key(_row_value(row, 5, "result_table")),
            "inputTables": [],
            "frequency": "",
            "changeType": "baseline",
            "source": "baseline",
        })
    return programs


def _normalize_program(raw: dict, *, source: str) -> dict:
    path = _path(raw.get("programPath"))
    job = _text(raw.get("jobName"))
    return {
        "lineageKey": _text(raw.get("lineageKey")) or (f"job:{_job_key(job)}" if job else f"program:{path.casefold()}"),
        "programPath": path,
        "scriptName": _text(raw.get("scriptName")) or PurePosixPath(path).name,
        "jobName": job,
        "resultTable": _table_key(raw.get("resultTable")),
        "inputTables": sorted({_table_key(item) for item in raw.get("inputTables") or [] if _table_key(item)}),
        "dependencyJobs": sorted({_text(item) for item in raw.get("dependencyJobs") or [] if _text(item)}, key=str.casefold),
        "frequency": _text(raw.get("frequency")),
        "disabled": bool(raw.get("disabled")),
        "changeType": _text(raw.get("changeType")) or ("baseline" if source == "baseline" else "modified"),
        "source": source,
    }


def _merge_programs(baseline: list[dict], overlay: dict) -> tuple[list[dict], dict[str, str]]:
    records: dict[str, dict] = {}
    path_index: dict[str, str] = {}
    job_index: dict[str, str] = {}
    aliases: dict[str, str] = {}

    def put(raw: dict, source: str) -> str:
        record = _normalize_program(raw, source=source)
        match = job_index.get(_job_key(record["jobName"])) if record["jobName"] else None
        if not match and record["programPath"]:
            match = path_index.get(record["programPath"].casefold())
        task_id = match or _task_id(record["jobName"], record["programPath"])
        if match:
            old = records[match]
            if old["jobName"]:
                job_index.pop(_job_key(old["jobName"]), None)
            if old["programPath"]:
                path_index.pop(old["programPath"].casefold(), None)
        records[task_id] = record
        if record["jobName"]:
            job_index[_job_key(record["jobName"])] = task_id
            aliases[f"job:{_job_key(record['jobName'])}"] = task_id
        if record["programPath"]:
            path_index[record["programPath"].casefold()] = task_id
            aliases[f"program:{record['programPath'].casefold()}"] = task_id
        aliases[record["lineageKey"]] = task_id
        return task_id

    for raw in baseline:
        put(raw, "baseline")
    for raw in overlay.get("programs") or []:
        put(raw, "current_change")
    return sorted(records.items()), aliases


def _build_graph(programs: list[tuple[str, dict]]) -> tuple[list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}
    result_by_job = {_job_key(item["jobName"]): item["resultTable"] for _, item in programs if item["jobName"] and item["resultTable"]}

    def table_node(name: str):
        if not name:
            return None
        node_id = _table_id(name)
        nodes.setdefault(node_id, {
            "id": node_id, "kind": "table", "name": name,
            "displayName": name, "namespace": name.split(".", 1)[0] if "." in name else "table",
            "attributes": {},
        })
        return node_id

    def add_edge(source_id: str, target_id: str, kind: str, program: dict):
        key = (source_id, target_id, kind)
        evidence_source = program["source"]
        edges[key] = {
            "id": _edge_id(*key), "sourceId": source_id, "targetId": target_id, "kind": kind,
            "evidence": {
                "type": evidence_source,
                "sourceRecordId": program["lineageKey"],
                "description": "本次审查修改" if evidence_source == "current_change" else "生产调度元数据",
            },
            "confidence": "high", "generatedAt": datetime.now(timezone.utc).isoformat(), "diagnostics": [],
        }

    for task_id, program in programs:
        nodes[task_id] = {
            "id": task_id, "kind": "task", "name": program["scriptName"] or program["jobName"],
            "displayName": program["jobName"] or "未关联调度作业", "namespace": "python",
            "attributes": {
                "programPath": program["programPath"], "jobName": program["jobName"],
                "resultTable": program["resultTable"], "frequency": program["frequency"],
                "disabled": program["disabled"], "changeType": program["changeType"], "source": program["source"],
            },
        }
        for table in program["inputTables"]:
            source_id = table_node(table)
            if source_id:
                add_edge(source_id, task_id, "script_reads_table", program)
        for dependency_job in program["dependencyJobs"]:
            dependency_table = result_by_job.get(_job_key(dependency_job))
            source_id = table_node(dependency_table)
            if source_id:
                add_edge(source_id, task_id, "schedule_dependency", program)
        target_id = table_node(program["resultTable"])
        if target_id:
            add_edge(task_id, target_id, "script_writes_table", program)
    return sorted(nodes.values(), key=lambda node: node["id"]), sorted(edges.values(), key=lambda edge: edge["id"])


def _subgraph(nodes: list[dict], edges: list[dict], root_id: str, direction: str, depth: int, max_nodes: int):
    selected = {root_id}
    queue = deque([(root_id, 0)])
    truncated = False
    while queue:
        current, level = queue.popleft()
        if level >= depth:
            continue
        neighbors = []
        for edge in edges:
            if direction in {"downstream", "both"} and edge["sourceId"] == current:
                neighbors.append(edge["targetId"])
            if direction in {"upstream", "both"} and edge["targetId"] == current:
                neighbors.append(edge["sourceId"])
        for neighbor in sorted(set(neighbors)):
            if neighbor in selected:
                continue
            if len(selected) >= max_nodes:
                truncated = True
                continue
            selected.add(neighbor)
            queue.append((neighbor, level + 1))
    return (
        [node for node in nodes if node["id"] in selected],
        [edge for edge in edges if edge["sourceId"] in selected and edge["targetId"] in selected],
        truncated,
    )


def get_task_lineage_subgraph(task_id: int, root_key: str | None, direction="both", depth=None, max_nodes=None) -> dict:
    task = get_task(task_id)
    if task.get("workflow") != "hcyt":
        raise ServiceError("lineage is only available for HCYT audit tasks", status_code=422)
    root_key = _text(root_key)
    if not root_key:
        raise ServiceError("rootKey is required", status_code=422)
    direction = _text(direction) or "both"
    if direction not in DIRECTIONS:
        raise ServiceError("direction must be upstream, downstream, or both", status_code=422)
    depth_value = _bounded_int(depth, default=3, minimum=1, maximum=5, name="depth")
    max_nodes_value = _bounded_int(max_nodes, default=100, minimum=1, maximum=200, name="maxNodes")
    try:
        report = json.loads(get_report_json(task_id))
    except ValueError as exc:
        raise ServiceError("task report is invalid", status_code=500) from exc
    overlay = report.get("lineageOverlay") or build_lineage_overlay(
        report.get("pyScripts") or [],
        revision=report.get("task", {}).get("revision", ""),
        changes=report.get("changes") or [],
    )
    diagnostics = []
    baseline_generated_at = datetime.now(timezone.utc).isoformat()
    profile = _text(report.get("metadataProfile")) or get_metadata_profile().name
    try:
        baseline = load_baseline_programs(profile)
    except Exception as exc:
        baseline = []
        diagnostics.append({"code": "BASELINE_UNAVAILABLE", "message": f"production metadata unavailable: {type(exc).__name__}"})
    programs, aliases = _merge_programs(baseline, overlay)
    root_id = aliases.get(root_key)
    if not root_id:
        raise ServiceError("lineage root was not found in this audit task", status_code=404)
    nodes, edges = _build_graph(programs)
    selected_nodes, selected_edges, truncated = _subgraph(nodes, edges, root_id, direction, depth_value, max_nodes_value)
    return {
        "rootId": root_id,
        "nodes": selected_nodes,
        "edges": selected_edges,
        "truncated": truncated,
        "diagnostics": diagnostics,
        "baselineGeneratedAt": baseline_generated_at,
        "overlayRevision": _text(overlay.get("revision")),
    }
