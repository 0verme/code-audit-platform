# -*- coding: utf-8 -*-
"""Audit run task state models.

This module intentionally has no Flask or database dependency. It gives the
executor/API layers a small in-memory model for reporting module-level progress
without changing the existing synchronous compatibility path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


TERMINAL_STATUSES = {
    AuditTaskStatus.SUCCESS,
    AuditTaskStatus.SKIPPED,
    AuditTaskStatus.FAILED,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


@dataclass(frozen=True)
class AuditTask:
    key: str
    label: str
    dependencies: tuple[str, ...] = ()
    weight: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("AuditTask.key is required")
        if not self.label:
            raise ValueError("AuditTask.label is required")
        if self.weight <= 0:
            raise ValueError("AuditTask.weight must be greater than 0")
        object.__setattr__(self, "dependencies", tuple(self.dependencies or ()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "dependencies": list(self.dependencies),
            "weight": self.weight,
            "metadata": _json_safe(self.metadata),
        }


@dataclass
class AuditTaskState:
    task: AuditTask
    status: AuditTaskStatus = AuditTaskStatus.QUEUED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    result: Any = None

    def mark_running(self, now: datetime | None = None) -> None:
        self.status = AuditTaskStatus.RUNNING
        self.started_at = now or _utc_now()
        self.finished_at = None
        self.duration_ms = None
        self.error = None

    def mark_success(
        self,
        result: Any = None,
        summary: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._finish(AuditTaskStatus.SUCCESS, result=result, summary=summary, now=now)

    def mark_skipped(
        self,
        reason: str = "",
        summary: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._finish(AuditTaskStatus.SKIPPED, error=reason or None, summary=summary, now=now)

    def mark_failed(
        self,
        error: Exception | str,
        summary: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self._finish(AuditTaskStatus.FAILED, error=str(error), summary=summary, now=now)

    def _finish(
        self,
        status: AuditTaskStatus,
        *,
        result: Any = None,
        error: str | None = None,
        summary: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        finished_at = now or _utc_now()
        if self.started_at is None:
            self.started_at = finished_at
        self.status = status
        self.finished_at = finished_at
        self.duration_ms = max(0, int((finished_at - self.started_at).total_seconds() * 1000))
        self.error = error
        self.result = result
        if summary is not None:
            self.summary = dict(summary)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_dict(self, include_result: bool = False) -> dict[str, Any]:
        payload = {
            "task": self.task.to_dict(),
            "status": self.status.value,
            "startedAt": _json_safe(self.started_at),
            "finishedAt": _json_safe(self.finished_at),
            "durationMs": self.duration_ms,
            "error": self.error,
            "summary": _json_safe(self.summary),
        }
        if include_result:
            payload["result"] = _json_safe(self.result)
        return payload


@dataclass
class AuditRunState:
    run_id: int | str
    workflow: str
    status: AuditTaskStatus = AuditTaskStatus.QUEUED
    tasks: dict[str, AuditTaskState] = field(default_factory=dict)
    partial_report: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=_utc_now)
    finished_at: datetime | None = None
    error: str | None = None

    def add_task(self, task: AuditTask) -> AuditTaskState:
        if task.key in self.tasks:
            raise ValueError(f"duplicate audit task key: {task.key}")
        state = AuditTaskState(task=task)
        self.tasks[task.key] = state
        return state

    def get_task(self, key: str) -> AuditTaskState:
        try:
            return self.tasks[key]
        except KeyError as exc:
            raise KeyError(f"unknown audit task key: {key}") from exc

    def mark_running(self) -> None:
        self.status = AuditTaskStatus.RUNNING

    def mark_finished(self, error: Exception | str | None = None) -> None:
        self.finished_at = _utc_now()
        self.error = str(error) if error else None
        self.status = AuditTaskStatus.FAILED if error else AuditTaskStatus.SUCCESS

    def ready_tasks(self) -> list[AuditTaskState]:
        result = []
        for state in self.tasks.values():
            if state.status != AuditTaskStatus.QUEUED:
                continue
            if all(self.get_task(dep).is_terminal for dep in state.task.dependencies):
                result.append(state)
        return result

    def set_section(self, key: str, value: Any) -> None:
        self.partial_report[key] = value

    def add_log(self, message: str, level: str = "INFO", now: datetime | None = None) -> None:
        self.logs.append({
            "ts": (now or _utc_now()).isoformat(),
            "level": level,
            "msg": str(message),
        })

    @property
    def progress(self) -> dict[str, Any]:
        total_weight = sum(state.task.weight for state in self.tasks.values())
        completed_weight = sum(
            state.task.weight for state in self.tasks.values() if state.is_terminal
        )
        running = [
            state.task.key for state in self.tasks.values()
            if state.status == AuditTaskStatus.RUNNING
        ]
        return {
            "total": len(self.tasks),
            "completed": sum(1 for state in self.tasks.values() if state.is_terminal),
            "totalWeight": total_weight,
            "completedWeight": completed_weight,
            "percent": 100 if total_weight == 0 else int(completed_weight * 100 / total_weight),
            "running": running,
        }

    def to_dict(self, include_results: bool = False) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "workflow": self.workflow,
            "status": self.status.value,
            "startedAt": _json_safe(self.started_at),
            "finishedAt": _json_safe(self.finished_at),
            "error": self.error,
            "progress": self.progress,
            "tasks": {
                key: state.to_dict(include_result=include_results)
                for key, state in self.tasks.items()
            },
            "partialReport": _json_safe(self.partial_report),
            "logs": _json_safe(self.logs),
        }
