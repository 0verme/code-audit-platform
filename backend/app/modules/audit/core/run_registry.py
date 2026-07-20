from __future__ import annotations

import threading

from ..compat import build_audit_run_partial_result_payload
from app.db.runtime_store import get_task_run_snapshot

try:
    from .run_state import AuditRunState
except ImportError:  # pragma: no cover - direct module execution fallback
    from run import AuditRunState


_run_state_lock = threading.RLock()
_run_states: dict[int, AuditRunState] = {}


def create_audit_run_state(task_id: int, workflow: str, tasks=()) -> AuditRunState:
    run_state = AuditRunState(run_id=task_id, workflow=workflow)
    for task in tasks:
        run_state.add_task(task)
    with _run_state_lock:
        _run_states[int(task_id)] = run_state
    return run_state


def get_audit_run_state(task_id: int) -> AuditRunState | None:
    with _run_state_lock:
        return _run_states.get(int(task_id))


def status_from_task_status(status: str) -> str:
    if status in {"running", "queued"}:
        return "running"
    if status in {"pass", "warn", "fail"}:
        return "success"
    return "failed"


def get_audit_run_status(task_id: int) -> dict | None:
    snapshot = get_task_run_snapshot(task_id, include_report=False)
    if snapshot is None:
        return None
    return _build_audit_run_status(task_id, snapshot)


def _build_audit_run_status(task_id: int, snapshot: dict) -> dict:
    task = snapshot["task"]
    run_state = get_audit_run_state(task_id)
    if run_state is not None:
        payload = run_state.to_dict(include_results=False)
    else:
        payload = {
            "runId": task_id,
            "workflow": task.get("workflow", ""),
            "status": status_from_task_status(task.get("status", "")),
            "progress": {
                "percent": int(task.get("progress") or 0),
                "running": [task.get("step")] if task.get("step") else [],
            },
            "tasks": {},
            "partialReport": {},
            "logs": task.get("logs", []),
        }

    payload["task"] = task
    if task.get("step") == "persistence_failed":
        payload["status"] = "failed"
    elif snapshot["finalReportReady"]:
        payload["status"] = status_from_task_status(task.get("status", ""))
    elif run_state is not None and run_state.status.value == "failed":
        payload["status"] = "failed"
    elif task.get("status") == "fail":
        payload["status"] = "failed"
    else:
        payload["status"] = status_from_task_status(task.get("status", ""))
    payload["taskStatus"] = task.get("status")
    payload["finalReportReady"] = snapshot["finalReportReady"]
    return payload


def get_audit_run_partial_result(task_id: int) -> dict | None:
    snapshot = get_task_run_snapshot(task_id, include_report=True)
    if snapshot is None:
        return None

    status_payload = _build_audit_run_status(task_id, snapshot)
    return build_audit_run_partial_result_payload(task_id, status_payload, snapshot["report"])
