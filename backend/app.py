from __future__ import annotations

import json
import re
import shutil
from datetime import datetime

from runtime_security import get_runtime_security_settings, load_backend_dotenv

load_backend_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS

import audit.engine as audit_engine
from audit.checks.workspace_service import validate_local_workspace
from audit.source_resolver import UnsupportedAuditSourceError, validate_supported_source_type
from db.runtime_store import (
    fail_orphan_tasks,
    get_audit_task as load_audit_task,
    get_task_report_row,
    list_audit_results,
    list_audit_tasks,
    list_fine_report_items,
    list_projects,
)
from db.connection import connect
from db.profiles import get_active_profile
from db.sql_runner import execute_insert


app = Flask(__name__)


def configure_runtime_security():
    settings = get_runtime_security_settings()
    CORS(app, resources={r"/api/*": {"origins": list(settings.cors_origins)}})
    return settings


configure_runtime_security()


fail_orphan_tasks()


TASK_COLUMNS = """
    id, repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
    started_at, duration, ai_enabled, debug_enabled, progress, step, finished_at,
    error, logs_json, source_type
"""


def normalize_source_type(value: str | None) -> str:
    source_type = str(value or "").strip().lower()
    if source_type == "local_dir":
        return "local"
    if source_type in {"local", "svn", "git", "selfcheck", "unknown"}:
        return source_type
    return ""


def infer_source_type(source_ref: str | None) -> str:
    value = str(source_ref or "").strip()
    lower = value.lower()
    if not value:
        return "unknown"
    if lower.startswith("local-selfcheck") or "selfcheck" in lower:
        return "selfcheck"
    if lower.startswith("svn://") or lower.startswith("svn+ssh://"):
        return "svn"
    if lower.startswith("git://") or re.match(r"^[^@\s]+@[^:\s]+:.+", value) or re.match(r"^ssh://[^/]+/.+", lower):
        return "git"
    if re.match(r"^https?://", lower):
        if lower.endswith(".git") or "/git/" in lower or "git." in lower or "/repos/" in lower:
            return "git"
    if re.match(r"^[a-zA-Z]:[\\/]", value) or lower.startswith("/") or lower.startswith("./") or lower.startswith("../"):
        return "local"
    return "unknown"


def extract_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


def task_row_to_dict(row):
    task = dict(row)
    try:
        task["logs"] = json.loads(task.pop("logs_json") or "[]")
    except (TypeError, ValueError):
        task["logs"] = []
    task["source_ref"] = task.get("source_ref") or task.get("repo") or ""
    inferred_source_type = infer_source_type(task["source_ref"])
    task["source_type"] = normalize_source_type(task.get("source_type")) or inferred_source_type
    if task["source_type"] == "svn" and inferred_source_type in {"git", "local", "selfcheck"}:
        task["source_type"] = inferred_source_type
    task["sourceRef"] = task["source_ref"]
    task["sourceType"] = task["source_type"]
    task["operator_user"] = task.get("operator_user") or task.get("author") or ""
    task["client_ip"] = task.get("client_ip") or ""
    return task


@app.get("/api/health")
def health():
    profile = get_active_profile()
    database = {"profile": profile.name, "type": profile.type, "connected": False}
    try:
        with connect(profile) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        database["connected"] = True
    except Exception:
        return jsonify({"status": "degraded", "database": database, "svn": {"cliAvailable": bool(shutil.which("svn"))}}), 503
    return jsonify({"status": "ok", "database": database, "svn": {"cliAvailable": bool(shutil.which("svn"))}})


@app.get("/api/projects")
def get_projects():
    rows = list_projects()
    return jsonify([dict(row) for row in rows])


@app.get("/api/audit-tasks")
def get_audit_tasks():
    rows = list_audit_tasks()
    return jsonify([task_row_to_dict(row) for row in rows])


@app.get("/api/audit-tasks/<int:task_id>")
def get_audit_task(task_id: int):
    row = load_audit_task(task_id)
    if row is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task_row_to_dict(row))


@app.get("/api/audit-tasks/<int:task_id>/report")
def get_audit_task_report(task_id: int):
    row = get_task_report_row(task_id)
    if row is None:
        return jsonify({"error": "report not ready"}), 404
    return app.response_class(row["report_json"], mimetype="application/json")


@app.get("/api/audit-runs/<int:run_id>/status")
def get_audit_run_status(run_id: int):
    payload = audit_engine.get_audit_run_status(run_id)
    if payload is None:
        return jsonify({"error": "audit run not found"}), 404
    return jsonify(payload)


@app.get("/api/audit-runs/<int:run_id>/partial-result")
def get_audit_run_partial_result(run_id: int):
    payload = audit_engine.get_audit_run_partial_result(run_id)
    if payload is None:
        return jsonify({"error": "audit run not found"}), 404
    return jsonify(payload)


@app.post("/api/audit-tasks")
def create_audit_task():
    payload = request.get_json(silent=True) or {}
    source_ref = (
        payload.get("sourceRef")
        or payload.get("source_ref")
        or payload.get("repo")
        or payload.get("path")
        or payload.get("workspaceRoot")
        or payload.get("workspace_root")
        or payload.get("localPath")
        or payload.get("local_path")
        or payload.get("targetPath")
        or payload.get("target_path")
        or payload.get("workspacePath")
        or payload.get("workspace_path")
        or ""
    ).strip()
    source_type = normalize_source_type(payload.get("sourceType") or payload.get("source_type")) or infer_source_type(source_ref)

    if not source_ref:
        return jsonify({"error": "sourceRef is required"}), 400
    if source_type == "unknown":
        return jsonify({"error": "sourceType is unknown and could not be inferred"}), 400
    try:
        source_type = validate_supported_source_type(source_type)
    except UnsupportedAuditSourceError as exc:
        return jsonify({"error": str(exc), "errorCode": "unsupported_audit_source"}), 400

    if source_type == "local":
        settings = get_runtime_security_settings()
        if not settings.local_source_enabled:
            app.logger.warning("Rejected disabled local workspace audit request")
            return jsonify({"errorCode": "local_source_disabled", "error": "Local workspace audit source is disabled."}), 403
        try:
            validate_local_workspace(source_ref, settings)
        except (OSError, ValueError, PermissionError) as exc:
            app.logger.warning("Rejected local workspace audit request: %s", exc)
            return jsonify({"errorCode": "local_source_not_allowed", "error": "Local workspace path is not allowed."}), 400

    workflow = audit_engine.detect_workflow(source_ref, payload.get("workflow", "hcyt"))
    if source_type == "local":
        workflow = (payload.get("workflow") or "hcyt").strip().lower()
        if workflow != "hcyt":
            return jsonify({"error": "local source currently supports hcyt workflow only"}), 400

    revision = payload.get("revision") or "-"
    operator_user = (payload.get("operator_user") or payload.get("author") or "local-user").strip() or "local-user"
    client_ip = (payload.get("client_ip") or extract_client_ip()).strip()
    ai_enabled = bool(payload.get("ai_enabled"))
    debug_enabled = bool(payload.get("debug_enabled"))
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    task_id = execute_insert(
        """
        INSERT INTO {{table:audit_tasks}} (
            repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
            started_at, duration, ai_enabled, debug_enabled, progress, step, source_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_ref,
            source_ref,
            workflow,
            "running",
            revision,
            operator_user,
            operator_user,
            client_ip,
            started_at,
            "0s",
            int(ai_enabled),
            int(debug_enabled),
            0,
            "queued",
            source_type,
        ),
    )

    audit_engine.start_task(task_id, source_ref, workflow, ai_enabled, debug_enabled, operator_user, source_type)
    return jsonify(
        {
            "id": task_id,
            "run_id": task_id,
            "runId": task_id,
            "repo": source_ref,
            "source_ref": source_ref,
            "source_type": source_type,
            "sourceRef": source_ref,
            "sourceType": source_type,
            "workflow": workflow,
            "operator_user": operator_user,
            "client_ip": client_ip,
            "status": "running",
        }
    ), 201


@app.post("/api/audit-runs")
def create_audit_run():
    return create_audit_task()


@app.get("/api/audit-results")
def get_audit_results():
    task_id = request.args.get("task_id", type=int)
    rows = list_audit_results(task_id)
    return jsonify([dict(row) for row in rows])


@app.get("/api/fine-report/items")
def get_fine_report_items():
    rows = list_fine_report_items()
    items = []
    for row in rows:
        item = dict(row)
        item["issues"] = json.loads(item.pop("issues_json"))
        item["ref_tables"] = json.loads(item.pop("ref_tables_json"))
        items.append(item)
    return jsonify(items)


if __name__ == "__main__":
    runtime_settings = get_runtime_security_settings()
    app.run(host=runtime_settings.host, port=runtime_settings.port, debug=runtime_settings.debug)
