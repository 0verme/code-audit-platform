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
from app.db.sql_runner import execute_insert, execute_one
from app.modules.audit.source.workspace import validate_local_workspace
from app.modules.audit.source.resolver import (
    LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE,
    SUPPORTED_LOCAL_WORKFLOWS,
    UnsupportedAuditSourceError,
    resolve_workflow,
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


def _load_task_by_idempotency_key(idempotency_key: str) -> dict | None:
    row = execute_one(
        """SELECT id, repo, source_ref, workflow, status, revision, author,
                  operator_user, client_ip, source_type, ai_enabled, debug_enabled
           FROM {{table:audit_tasks}} WHERE idempotency_key = ?""",
        (idempotency_key,),
    )
    return dict(row) if row is not None else None


def _task_creation_response(task: dict, *, deduplicated: bool) -> dict:
    source_ref = task.get("source_ref") or task.get("repo") or ""
    source_type = normalize_source_type(task.get("source_type")) or infer_source_type(source_ref)
    return {
        "id": task["id"],
        "run_id": task["id"],
        "runId": task["id"],
        "repo": source_ref,
        "source_ref": source_ref,
        "source_type": source_type,
        "sourceRef": source_ref,
        "sourceType": source_type,
        "workflow": task["workflow"],
        "operator_user": task.get("operator_user") or task.get("author") or "",
        "client_ip": task.get("client_ip") or "",
        "status": task.get("status") or "running",
        "deduplicated": deduplicated,
    }


def _validate_idempotent_replay(
    task: dict,
    *,
    source_ref: str,
    source_type: str,
    workflow: str,
    ai_enabled: bool,
    debug_enabled: bool,
) -> None:
    existing_signature = (
        task.get("source_ref") or task.get("repo") or "",
        normalize_source_type(task.get("source_type")),
        task.get("workflow") or "",
        bool(task.get("ai_enabled")),
        bool(task.get("debug_enabled")),
    )
    requested_signature = (source_ref, source_type, workflow, ai_enabled, debug_enabled)
    if existing_signature != requested_signature:
        raise ServiceError(
            "Idempotency-Key was already used with different audit parameters.",
            status_code=409,
            payload={
                "error": "Idempotency-Key was already used with different audit parameters.",
                "errorCode": "idempotency_conflict",
            },
        )


def create_task(payload: dict, *, client_ip: str, idempotency_key: str | None = None) -> dict:
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
    if source_type == "local":
        workflow = str(payload.get("workflow") or "hcyt").strip().lower()
        if workflow not in SUPPORTED_LOCAL_WORKFLOWS:
            raise ServiceError(LOCAL_WORKFLOW_UNSUPPORTED_MESSAGE, status_code=400)
    else:
        workflow = resolve_workflow(source_ref, payload.get("workflow", "hcyt"))
    operator_user = str(payload.get("operator_user") or payload.get("author") or "local-user").strip() or "local-user"
    effective_ip = str(payload.get("client_ip") or client_ip).strip()
    normalized_idempotency_key = str(idempotency_key or "").strip() or None
    if normalized_idempotency_key and len(normalized_idempotency_key) > 128:
        raise ServiceError("Idempotency-Key is too long.", status_code=400)
    ai_enabled = bool(payload.get("ai_enabled"))
    debug_enabled = bool(payload.get("debug_enabled"))

    if normalized_idempotency_key:
        existing = _load_task_by_idempotency_key(normalized_idempotency_key)
        if existing is not None:
            _validate_idempotent_replay(
                existing,
                source_ref=source_ref,
                source_type=source_type,
                workflow=workflow,
                ai_enabled=ai_enabled,
                debug_enabled=debug_enabled,
            )
            return _task_creation_response(existing, deduplicated=True)

    insert_sql = """INSERT INTO {{table:audit_tasks}} (
            repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
            started_at, duration, ai_enabled, debug_enabled, progress, step, source_type,
            idempotency_key
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    insert_params = (
        source_ref, source_ref, workflow, "running", payload.get("revision") or "-", operator_user,
        operator_user, effective_ip, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "0s",
        int(ai_enabled), int(debug_enabled), 0, "queued", source_type, normalized_idempotency_key,
    )
    try:
        task_id = execute_insert(insert_sql, insert_params)
    except Exception:
        existing = (
            _load_task_by_idempotency_key(normalized_idempotency_key)
            if normalized_idempotency_key
            else None
        )
        if existing is None:
            raise
        _validate_idempotent_replay(
            existing,
            source_ref=source_ref,
            source_type=source_type,
            workflow=workflow,
            ai_enabled=ai_enabled,
            debug_enabled=debug_enabled,
        )
        return _task_creation_response(existing, deduplicated=True)

    task = {
        "id": task_id,
        "repo": source_ref,
        "source_ref": source_ref,
        "workflow": workflow,
        "status": "running",
        "operator_user": operator_user,
        "client_ip": effective_ip,
        "source_type": source_type,
    }
    audit_engine.start_task(task_id, source_ref, workflow, ai_enabled, debug_enabled, operator_user, source_type)
    return _task_creation_response(task, deduplicated=False)
