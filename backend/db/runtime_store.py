from __future__ import annotations

import json
from dataclasses import dataclass

from audit.compat import normalize_legacy_audit_result_groups

from .connection import get_connection


class TaskCompletionValidationError(ValueError):
    """Raised when an atomic task completion cannot be applied safely."""


@dataclass(frozen=True)
class AtomicTaskCompletionResult:
    """Committed outcome of ``persist_task_completion_atomic``."""

    task_id: int
    report_written: bool
    results_written: int


TASK_COLUMNS = """
    id, repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
    started_at, duration, ai_enabled, debug_enabled, progress, step, finished_at,
    error, logs_json, source_type
"""


def fail_orphan_tasks() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE {{table:audit_tasks}}
            SET status = 'fail', step = 'interrupted', error = 'backend restarted while task was running'
            WHERE status IN ('running', 'queued')
            """
        )


def list_projects():
    with get_connection() as connection:
        return connection.execute(
            "SELECT id, name, project_key, repo_path, workflow, description FROM {{table:projects}} ORDER BY id"
        ).fetchall()


def list_audit_tasks():
    with get_connection() as connection:
        return connection.execute(f"SELECT {TASK_COLUMNS} FROM {{{{table:audit_tasks}}}} ORDER BY id DESC").fetchall()


def get_audit_task(task_id: int):
    with get_connection() as connection:
        return connection.execute(f"SELECT {TASK_COLUMNS} FROM {{{{table:audit_tasks}}}} WHERE id = ?", (task_id,)).fetchone()


def get_task_row_payload(task_id: int) -> dict | None:
    row = get_audit_task(task_id)
    if row is None:
        return None
    payload = dict(row)
    try:
        payload["logs"] = json.loads(payload.pop("logs_json") or "[]")
    except (TypeError, ValueError):
        payload["logs"] = []
    return payload


def get_task_report_row(task_id: int):
    with get_connection() as connection:
        return connection.execute("SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?", (task_id,)).fetchone()


def get_task_report_payload(task_id: int) -> dict | None:
    row = get_task_report_row(task_id)
    if row is None:
        return None
    try:
        return json.loads(row["report_json"])
    except (TypeError, ValueError):
        return None


def build_task_report_json(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False)


def build_task_logs_json(logs: list[dict]) -> str:
    return json.dumps(logs, ensure_ascii=False)


def _upsert_task_report_with_connection(connection, task_id: int, report_json: str, created_at: str) -> None:
    """Replace one canonical report using the caller-owned transaction."""
    connection.execute("DELETE FROM {{table:task_reports}} WHERE task_id = ?", (task_id,))
    connection.execute(
        "INSERT INTO {{table:task_reports}} (task_id, report_json, created_at) VALUES (?, ?, ?)",
        (task_id, report_json, created_at),
    )


def upsert_task_report(task_id: int, report_json: str, created_at: str) -> None:
    with get_connection() as connection:
        _upsert_task_report_with_connection(connection, task_id, report_json, created_at)


def update_task_runtime_state(task_id: int, logs_json: str, *, progress: int | None = None, step: str | None = None) -> None:
    with get_connection() as connection:
        sets, args = ["logs_json = ?"], [logs_json]
        if progress is not None:
            sets.append("progress = ?")
            args.append(int(progress))
        if step is not None:
            sets.append("step = ?")
            args.append(step)
        args.append(task_id)
        connection.execute(f"UPDATE {{table:audit_tasks}} SET {', '.join(sets)} WHERE id = ?", args)


def _update_task_with_connection(
    connection,
    task_id: int,
    *,
    status: str,
    duration: str,
    finished_at: str,
    error: str | None,
    progress: int,
    step: str,
    logs_json: str,
) -> int | None:
    cursor = connection.execute(
        """
        UPDATE {{table:audit_tasks}}
        SET status = ?, duration = ?, finished_at = ?, error = ?, progress = ?, step = ?, logs_json = ?
        WHERE id = ?
        """,
        (status, duration, finished_at, error, progress, step, logs_json, task_id),
    )
    return cursor.rowcount


def finalize_task(
    task_id: int,
    *,
    status: str,
    duration: str,
    finished_at: str,
    error: str | None,
    progress: int,
    step: str,
    logs_json: str,
) -> None:
    with get_connection() as connection:
        _update_task_with_connection(
            connection, task_id, status=status, duration=duration, finished_at=finished_at,
            error=error, progress=progress, step=step, logs_json=logs_json,
        )


def persist_task_run_completion(
    task_id: int,
    *,
    status: str,
    duration: str,
    finished_at: str,
    error: str | None,
    progress: int,
    step: str,
    logs: list[dict],
    report: dict | None = None,
) -> None:
    finalize_task(
        task_id,
        status=status,
        duration=duration,
        finished_at=finished_at,
        error=error,
        progress=progress,
        step=step,
        logs_json=build_task_logs_json(logs),
    )
    if report is not None:
        upsert_task_report(task_id, build_task_report_json(report), finished_at)


def build_audit_result_row_payloads(task_id: int, grouped_rows: dict[str, list[dict]]) -> list[tuple]:
    payloads = []
    for category, rows in normalize_legacy_audit_result_groups(grouped_rows).items():
        for row in rows:
            payloads.append(
                (
                    task_id,
                    category,
                    row["file"],
                    row["line"],
                    row["rule"],
                    row["level"],
                    row["msg"],
                )
            )
    return payloads


def _replace_audit_results_with_connection(connection, task_id: int, grouped_rows: dict[str, list[dict]]) -> int:
    """Replace legacy results using the caller-owned transaction.

    An empty group deliberately deletes the prior result set and leaves it empty.
    """
    row_payloads = build_audit_result_row_payloads(task_id, grouped_rows)
    connection.execute("DELETE FROM {{table:audit_results}} WHERE task_id = ?", (task_id,))
    for row_payload in row_payloads:
        connection.execute(
            """
            INSERT INTO {{table:audit_results}} (task_id, category, file_name, line_no, rule_name, level, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            row_payload,
        )
    return len(row_payloads)


def replace_audit_results(task_id: int, grouped_rows: dict[str, list[dict]]) -> None:
    with get_connection() as connection:
        _replace_audit_results_with_connection(connection, task_id, grouped_rows)


def persist_task_completion_atomic(
    task_id: int,
    *,
    status: str,
    duration: str,
    finished_at: str,
    error: str | None,
    progress: int,
    step: str,
    logs: list[dict],
    report: dict,
    audit_results: dict[str, list[dict]],
) -> AtomicTaskCompletionResult:
    """Atomically replace a task's completion, report, and compatibility rows.

    This repository-owned API opens exactly one connection.  Its context manager
    commits once after all writes succeed, or rolls back and closes on any error.
    Replays are compatible with the existing overwrite semantics: the last
    payload wins, while report and results remain single, replaced representations.
    """
    if not isinstance(task_id, int) or isinstance(task_id, bool) or task_id <= 0:
        raise TaskCompletionValidationError("task_id must be a positive integer")
    if not isinstance(report, dict):
        raise TaskCompletionValidationError("report must be a dictionary")
    if not isinstance(audit_results, dict):
        raise TaskCompletionValidationError("audit_results must be a dictionary")

    logs_json = build_task_logs_json(logs)
    report_json = build_task_report_json(report)
    with get_connection() as connection:
        task = connection.execute("SELECT id FROM {{table:audit_tasks}} WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            raise TaskCompletionValidationError(f"task {task_id} does not exist")
        _upsert_task_report_with_connection(connection, task_id, report_json, finished_at)
        results_written = _replace_audit_results_with_connection(connection, task_id, audit_results)
        updated = _update_task_with_connection(
            connection, task_id, status=status, duration=duration, finished_at=finished_at,
            error=error, progress=progress, step=step, logs_json=logs_json,
        )
        if updated != 1:
            raise TaskCompletionValidationError(f"task {task_id} was not updated")
    return AtomicTaskCompletionResult(task_id=task_id, report_written=True, results_written=results_written)


def list_audit_results(task_id: int | None = None):
    query = """
        SELECT id, task_id, category, file_name, line_no, rule_name, level, message
        FROM {{table:audit_results}}
    """
    args = ()
    if task_id is not None:
        query += " WHERE task_id = ?"
        args = (task_id,)
    query += " ORDER BY id"
    with get_connection() as connection:
        return connection.execute(query, args).fetchall()


def list_fine_report_items():
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, title, file_path, report_type, change_type, connection_name,
                   focus, dataset_sql, dataset_rows, issues_json, ref_tables_json
            FROM {{table:fine_report_items}}
            ORDER BY id
            """
        ).fetchall()
