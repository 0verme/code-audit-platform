from __future__ import annotations

import json
from dataclasses import dataclass

from app.modules.audit.compat import normalize_legacy_audit_result_groups

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

AUDIT_RESULT_INSERT_BATCH_SIZE = 100
TASK_IDEMPOTENCY_COLUMNS = """
    id, repo, source_ref, workflow, status, revision, author,
    operator_user, client_ip, source_type, ai_enabled, debug_enabled
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


def get_audit_task_by_idempotency_key(idempotency_key: str):
    with get_connection() as connection:
        return connection.execute(
            f"SELECT {TASK_IDEMPOTENCY_COLUMNS} FROM {{{{table:audit_tasks}}}} WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()


def create_audit_task(
    *,
    source_ref: str,
    workflow: str,
    revision: str,
    operator_user: str,
    client_ip: str,
    started_at: str,
    ai_enabled: bool,
    debug_enabled: bool,
    source_type: str,
    idempotency_key: str | None,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO {{table:audit_tasks}} (
                repo, source_ref, workflow, status, revision, author, operator_user, client_ip,
                started_at, duration, ai_enabled, debug_enabled, progress, step, source_type,
                idempotency_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                idempotency_key,
            ),
            expect_lastrowid=True,
        )
        return int(cursor.lastrowid)


def is_unique_constraint_error(error: BaseException) -> bool:
    """Recognize cross-driver unique violations without swallowing other DB failures."""

    current: BaseException | None = error
    while current is not None:
        if getattr(current, "sqlstate", None) == "23505" or getattr(current, "pgcode", None) == "23505":
            return True
        if current.__class__.__name__ in {"IntegrityError", "UniqueViolation"}:
            message = str(current).lower()
            if "unique" in message or "duplicate" in message:
                return True
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, BaseException) else None
    return False


def get_task_row_payload(task_id: int) -> dict | None:
    row = get_audit_task(task_id)
    return _build_task_row_payload(row)


def _build_task_row_payload(row) -> dict | None:
    if row is None:
        return None
    payload = dict(row)
    try:
        payload["logs"] = json.loads(payload.pop("logs_json") or "[]")
    except (TypeError, ValueError):
        payload["logs"] = []
    return payload


def get_task_run_snapshot(task_id: int, *, include_report: bool = True) -> dict | None:
    """Read task state and report readiness through one runtime DB connection."""
    with get_connection() as connection:
        task_row = connection.execute(
            f"SELECT {TASK_COLUMNS} FROM {{{{table:audit_tasks}}}} WHERE id = ?",
            (task_id,),
        ).fetchone()
        if task_row is None:
            return None
        if include_report:
            report_row = connection.execute(
                "SELECT report_json FROM {{table:task_reports}} WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        else:
            report_row = connection.execute(
                "SELECT 1 AS report_exists FROM {{table:task_reports}} WHERE task_id = ?",
                (task_id,),
            ).fetchone()

    report = None
    if include_report and report_row is not None:
        try:
            report = json.loads(report_row["report_json"])
        except (TypeError, ValueError):
            report = None
    return {
        "task": _build_task_row_payload(task_row),
        "report": report,
        "finalReportReady": report_row is not None and (not include_report or report is not None),
    }


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
        connection.execute(f"UPDATE {{{{table:audit_tasks}}}} SET {', '.join(sets)} WHERE id = ?", args)


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


def finalize_task_persistence_failure(
    task_id: int,
    *,
    duration: str,
    finished_at: str,
    error: str,
    logs: list[dict],
) -> None:
    """Publish a durable failure after an atomic completion transaction rolls back."""
    finalize_task(
        task_id,
        status="fail",
        duration=duration,
        finished_at=finished_at,
        error=error,
        progress=95,
        step="persistence_failed",
        logs_json=build_task_logs_json(logs),
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
    for offset in range(0, len(row_payloads), AUDIT_RESULT_INSERT_BATCH_SIZE):
        batch = row_payloads[offset:offset + AUDIT_RESULT_INSERT_BATCH_SIZE]
        placeholders = ", ".join("(?, ?, ?, ?, ?, ?)" for _row in batch)
        parameters = tuple(value for row in batch for value in row)
        connection.execute(
            f"""
            INSERT INTO {{{{table:audit_results}}}}
                (task_id, category, file_name, rule_name, level, message)
            VALUES {placeholders}
            """,
            parameters,
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
        # Some JDBC drivers report -1/None for a successful DML statement.
        # The task was verified immediately above in the same transaction, so
        # only a definite zero or a conflicting positive count is a failure.
        if updated == 0 or (isinstance(updated, int) and updated > 1):
            raise TaskCompletionValidationError(f"task {task_id} was not updated")
    return AtomicTaskCompletionResult(task_id=task_id, report_written=True, results_written=results_written)


def list_audit_results(task_id: int | None = None):
    query = """
        SELECT id, task_id, category, file_name, rule_name, level, message
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
