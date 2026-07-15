from __future__ import annotations

import json
import re
from datetime import datetime

import app.modules.audit.engine as audit_engine
from app.db.runtime_store import (
    fail_orphan_tasks,
    get_audit_task as load_audit_task,
    get_task_report_row,
    list_audit_tasks,
)
from app.db.sql_runner import execute_insert
from app.modules.audit.checks.workspace_service import validate_local_workspace
from app.modules.audit.source_resolver import (
    LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE,
    SUPPORTED_LOCAL_WORKFLOWS,
    UnsupportedAuditSourceError,
    validate_supported_source_type,
)
from app.settings import get_runtime_security_settings
from . import ServiceError


def recover_orphan_tasks() -> None:
    fail_orphan_tasks()


def normalize_source_type(value: str | None) -> str:
    source_type = str(value or "").strip().lower()
    if source_type == "local_dir":
        return "local"
    return source_type if source_type in {"local", "svn", "git", "selfcheck", "unknown"} else ""


def infer_source_type(source_ref: str | None) -> str:
    value = str(source_ref or "").strip()
    lower = value.lower()
    if not value:
        return "unknown"
    if lower.startswith("local-selfcheck") or "selfcheck" in lower:
        return "selfcheck"
    if lower.startswith(("svn://", "svn+ssh://")):
        return "svn"
    if lower.startswith("git://") or re.match(r"^[^@\s]+@[^:\s]+:.+", value) or re.match(r"^ssh://[^/]+/.+", lower):
        return "git"
    if re.match(r"^https?://", lower) and (lower.endswith(".git") or "/git/" in lower or "git." in lower or "/repos/" in lower):
        return "git"
    if re.match(r"^[a-zA-Z]:[\\/]", value) or lower.startswith(("/", "./", "../")):
        return "local"
    return "unknown"


def task_row_to_dict(row) -> dict:
    task = dict(row)
    try:
        task["logs"] = json.loads(task.pop("logs_json") or "[]")
    except (TypeError, ValueError):
        task["logs"] = []
    task["source_ref"] = task.get("source_ref") or task.get("repo") or ""
    inferred = infer_source_type(task["source_ref"])
    task["source_type"] = normalize_source_type(task.get("source_type")) or inferred
    if task["source_type"] == "svn" and inferred in {"git", "local", "selfcheck"}:
        task["source_type"] = inferred
    task["sourceRef"] = task["source_ref"]
    task["sourceType"] = task["source_type"]
    task["operator_user"] = task.get("operator_user") or task.get("author") or ""
    task["client_ip"] = task.get("client_ip") or ""
    return task


def get_tasks() -> list[dict]:
    return [task_row_to_dict(row) for row in list_audit_tasks()]


def get_task(task_id: int) -> dict:
    row = load_audit_task(task_id)
    if row is None:
        raise ServiceError("task not found", status_code=404)
    return task_row_to_dict(row)


def get_report_json(task_id: int) -> str:
    row = get_task_report_row(task_id)
    if row is None:
        raise ServiceError("report not ready", status_code=404)
    return row["report_json"]


def create_task(payload: dict, *, client_ip: str) -> dict:
    source_ref = next((str(payload.get(key) or "").strip() for key in (
        "sourceRef", "source_ref", "repo", "path", "workspaceRoot", "workspace_root",
        "localPath", "local_path", "targetPath", "target_path", "workspacePath", "workspace_path",
    ) if str(payload.get(key) or "").strip()), "")
    source_type = normalize_source_type(payload.get("sourceType") or payload.get("source_type")) or infer_source_type(source_ref)
    if not source_ref:
        raise ServiceError("sourceRef is required", status_code=400)
    if source_type == "unknown":
        raise ServiceError("sourceType is unknown and could not be inferred", status_code=400)
    try:
        source_type = validate_supported_source_type(source_type)
    except UnsupportedAuditSourceError as exc:
        raise ServiceError(str(exc), status_code=400, payload={"error": str(exc), "errorCode": "unsupported_audit_source"}) from exc
    if source_type == "local":
        settings = get_runtime_security_settings()
        if not settings.local_source_enabled:
            raise ServiceError("Local workspace audit source is disabled.", status_code=403, payload={"errorCode": "local_source_disabled", "error": "Local workspace audit source is disabled."})
        try:
            validate_local_workspace(source_ref, settings)
        except (OSError, ValueError, PermissionError) as exc:
            raise ServiceError("Local workspace path is not allowed.", status_code=400, payload={"errorCode": "local_source_not_allowed", "error": "Local workspace path is not allowed."}) from exc
    workflow = audit_engine.detect_workflow(source_ref, payload.get("workflow", "hcyt"))
    if source_type == "local":
        workflow = str(payload.get("workflow") or "hcyt").strip().lower()
        if workflow not in SUPPORTED_LOCAL_WORKFLOWS:
            raise ServiceError(LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE, status_code=400)
    operator_user = str(payload.get("operator_user") or payload.get("author") or "local-user").strip() or "local-user"
    effective_ip = str(payload.get("client_ip") or client_ip).strip()
    task_id = execute_insert(
        """INSERT INTO {{table:audit_tasks}} (
            repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
            started_at, duration, ai_enabled, debug_enabled, progress, step, source_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_ref, source_ref, workflow, "running", payload.get("revision") or "-", operator_user,
         operator_user, effective_ip, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "0s",
         int(bool(payload.get("ai_enabled"))), int(bool(payload.get("debug_enabled"))), 0, "queued", source_type),
    )
    audit_engine.start_task(task_id, source_ref, workflow, bool(payload.get("ai_enabled")), bool(payload.get("debug_enabled")), operator_user, source_type)
    return {"id": task_id, "run_id": task_id, "runId": task_id, "repo": source_ref,
            "source_ref": source_ref, "source_type": source_type, "sourceRef": source_ref,
            "sourceType": source_type, "workflow": workflow, "operator_user": operator_user,
            "client_ip": effective_ip, "status": "running"}
