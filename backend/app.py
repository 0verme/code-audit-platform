from __future__ import annotations

import json
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

from database import get_connection, init_db


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
init_db()


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
        rows = connection.execute(
            """
            SELECT id, repo, workflow, status, revision, author, started_at, duration,
                   ai_enabled, debug_enabled
            FROM audit_tasks
            ORDER BY id DESC
            """
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/audit-tasks")
def create_audit_task():
    payload = request.get_json(silent=True) or {}
    repo = payload.get("repo")
    workflow = payload.get("workflow", "hcyt")
    if not repo:
        return jsonify({"error": "repo is required"}), 400

    revision = payload.get("revision") or f"r{int(datetime.now().timestamp())}"
    author = payload.get("author") or "local-user"
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_tasks (
                repo, workflow, status, revision, author, started_at, duration,
                ai_enabled, debug_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo,
                workflow,
                "running",
                revision,
                author,
                started_at,
                "0秒",
                int(bool(payload.get("ai_enabled"))),
                int(bool(payload.get("debug_enabled"))),
            ),
        )
        task_id = cursor.lastrowid
    return jsonify({"id": task_id, "repo": repo, "workflow": workflow, "status": "running"}), 201


@app.get("/api/audit-results")
def get_audit_results():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, task_id, category, file_name, line_no, rule_name, level, message
            FROM audit_results
            ORDER BY id
            """
        ).fetchall()
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
