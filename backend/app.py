from __future__ import annotations

import json
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

from database import get_connection, init_db

import engine


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
init_db()


def _fail_orphan_tasks():
    """任务线程随进程退出（重启/热重载）后，把遗留的 running 任务标记为失败。"""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit_tasks
            SET status = 'fail', step = '中断', error = '后端重启导致任务中断，请重新提交审查'
            WHERE status IN ('running', 'queued')
            """
        )


_fail_orphan_tasks()


TASK_COLUMNS = """
    id, repo, workflow, status, revision, author, started_at, duration,
    ai_enabled, debug_enabled, progress, step, finished_at, error, logs_json, source_type
"""


def task_row_to_dict(row):
    task = dict(row)
    try:
        task["logs"] = json.loads(task.pop("logs_json") or "[]")
    except (TypeError, ValueError):
        task["logs"] = []
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
        rows = connection.execute(
            f"SELECT {TASK_COLUMNS} FROM audit_tasks ORDER BY id DESC"
        ).fetchall()
    return jsonify([task_row_to_dict(row) for row in rows])


@app.get("/api/audit-tasks/<int:task_id>")
def get_audit_task(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT {TASK_COLUMNS} FROM audit_tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task_row_to_dict(row))


@app.get("/api/audit-tasks/<int:task_id>/report")
def get_audit_task_report(task_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT report_json FROM task_reports WHERE task_id = ?", (task_id,)
        ).fetchone()
    if row is None:
        return jsonify({"error": "report not ready"}), 404
    return app.response_class(row["report_json"], mimetype="application/json")


@app.post("/api/audit-tasks")
def create_audit_task():
    payload = request.get_json(silent=True) or {}
    source_type = (payload.get("sourceType") or payload.get("source_type") or "svn").strip().lower()
    if source_type not in {"svn", "local"}:
        return jsonify({"error": "sourceType must be svn or local"}), 400

    repo = (
        payload.get("repo")
        or payload.get("workspaceRoot")
        or payload.get("workspace_root")
        or payload.get("localPath")
        or payload.get("local_path")
        or ""
    ).strip()
    if not repo:
        field = "localPath" if source_type == "local" else "repo"
        return jsonify({"error": f"{field} is required"}), 400

    workflow = engine.detect_workflow(repo, payload.get("workflow", "hcyt"))
    if source_type == "local":
        workflow = (payload.get("workflow") or "hcyt").strip().lower()
        if workflow != "hcyt":
            return jsonify({"error": "local source currently supports hcyt workflow only"}), 400
    revision = payload.get("revision") or "-"
    author = payload.get("author") or "local-user"
    ai_enabled = bool(payload.get("ai_enabled"))
    debug_enabled = bool(payload.get("debug_enabled"))
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_tasks (
                repo, workflow, status, revision, author, started_at, duration,
                ai_enabled, debug_enabled, progress, step, source_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo, workflow, "running", revision, author, started_at, "0秒",
                int(ai_enabled), int(debug_enabled), 0, "排队中", source_type,
            ),
        )
        task_id = cursor.lastrowid

    # 后台线程跑真实审查引擎（pytools_new/apps/svn_check）
    engine.start_task(task_id, repo, workflow, ai_enabled, debug_enabled, author, source_type)
    return jsonify({"id": task_id, "repo": repo, "workflow": workflow, "sourceType": source_type, "status": "running"}), 201


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
