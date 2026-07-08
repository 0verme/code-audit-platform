from __future__ import annotations

import json
import re
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

import engine
from database import execute_insert, get_connection, init_db


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
init_db()


def _fail_orphan_tasks():
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit_tasks
            SET status = 'fail', step = 'interrupted', error = 'backend restarted while task was running'
            WHERE status IN ('running', 'queued')
            """
        )


_fail_orphan_tasks()


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
    return jsonify({"status": "ok", "service": "code-review-platform-backend"})


@app.get("/api/projects")
def get_projects():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, project_key, repo_path, workflow, description FROM projects ORDER BY id"
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/audit-tasks")
def get_audit_tasks():
    with get_connection() as connection:
        rows = connection.execute(f"SELECT {TASK_COLUMNS} FROM audit_tasks ORDER BY id DESC").fetchall()
    return jsonify([task_row_to_dict(row) for row in rows])


@app.get("/api/audit-tasks/<int:task_id>")
def get_audit_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(f"SELECT {TASK_COLUMNS} FROM audit_tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task_row_to_dict(row))


@app.get("/api/audit-tasks/<int:task_id>/report")
def get_audit_task_report(task_id: int):
    with get_connection() as connection:
        row = connection.execute("SELECT report_json FROM task_reports WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        return jsonify({"error": "report not ready"}), 404
    return app.response_class(row["report_json"], mimetype="application/json")
@app.get("/api/audit-runs/<int:run_id>/status")
def get_audit_run_status(run_id: int):
    payload = engine.get_audit_run_status(run_id)
    if payload is None:
        return jsonify({"error": "audit run not found"}), 404
    return jsonify(payload)


@app.get("/api/audit-runs/<int:run_id>/partial-result")
def get_audit_run_partial_result(run_id: int):
    payload = engine.get_audit_run_partial_result(run_id)
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

    workflow = engine.detect_workflow(source_ref, payload.get("workflow", "hcyt"))
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
        INSERT INTO audit_tasks (
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

    engine.start_task(task_id, source_ref, workflow, ai_enabled, debug_enabled, operator_user, source_type)
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
    query = """
        SELECT id, task_id, category, file_name, line_no, rule_name, level, message
        FROM audit_results
    """
    args = ()
    if task_id is not None:
        query += " WHERE task_id = ?"
        args = (task_id,)
    query += " ORDER BY id"
    with get_connection() as connection:
        rows = connection.execute(query, args).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/fine-report/items")
def get_fine_report_items():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, title, file_path, report_type, change_type, connection_name,
                   focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            FROM fine_report_items
            ORDER BY id
            """
        ).fetchall()

    items = []
    for row in rows:
        item = dict(row)
        item["issues"] = json.loads(item.pop("issues_json"))
        item["ref_tables"] = json.loads(item.pop("ref_tables_json"))
        items.append(item)
    return jsonify(items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
