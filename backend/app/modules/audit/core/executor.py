# -*- coding: utf-8 -*-
"""Bounded audit task executor.

The executor is deliberately framework-agnostic. It runs prerequisites in order,
then schedules dependency-aware audit modules with a bounded thread pool, and
finally runs compatibility/finalizer tasks after every module has reached a
terminal state.
"""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

try:
    from .run_state import AuditRunState, AuditTask, AuditTaskStatus
except ImportError:  # pragma: no cover - direct backend script execution
    from run_state import AuditRunState, AuditTask, AuditTaskStatus


AuditTaskHandler = Callable[[AuditRunState], Any]
AuditSummaryBuilder = Callable[[Any], dict[str, Any]]


@dataclass(frozen=True)
class AuditTaskOutcome:
    result: Any = None
    summary: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutableAuditTask:
    task: AuditTask
    handler: AuditTaskHandler
    degrade_on_error: bool = True
    skip_on_failed_dependency: bool = True
    result_section: str | None = None
    summary_builder: AuditSummaryBuilder | None = None


class AuditExecutionError(RuntimeError):
    pass


class BoundedAuditExecutor:
    def __init__(self, max_workers: int = 4):
        if max_workers <= 0:
            raise ValueError("max_workers must be greater than 0")
        self.max_workers = max_workers

    def run(
        self,
        run_state: AuditRunState,
        prerequisites: Iterable[ExecutableAuditTask] = (),
        modules: Iterable[ExecutableAuditTask] = (),
        finalizers: Iterable[ExecutableAuditTask] = (),
    ) -> AuditRunState:
        prerequisite_tasks = list(prerequisites)
        module_tasks = list(modules)
        finalizer_tasks = list(finalizers)
        self._register(run_state, [*prerequisite_tasks, *module_tasks, *finalizer_tasks])

        run_state.mark_running()
        try:
            for task in prerequisite_tasks:
                self._execute_one(run_state, task)

            self._execute_modules(run_state, module_tasks)

            for task in finalizer_tasks:
                self._execute_one(run_state, task)
        except Exception as exc:
            run_state.mark_finished(error=exc)
            raise

        run_state.mark_finished()
        return run_state

    def _register(self, run_state: AuditRunState, tasks: list[ExecutableAuditTask]) -> None:
        for executable in tasks:
            if executable.task.key not in run_state.tasks:
                run_state.add_task(executable.task)

    def _execute_modules(self, run_state: AuditRunState, tasks: list[ExecutableAuditTask]) -> None:
        pending = {executable.task.key: executable for executable in tasks}
        futures: dict[Future[None], ExecutableAuditTask] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while pending or futures:
                self._skip_blocked_tasks(run_state, pending)
                ready = self._ready_executables(run_state, pending)
                while ready and len(futures) < self.max_workers:
                    executable = ready.pop(0)
                    pending.pop(executable.task.key, None)
                    futures[pool.submit(self._execute_one, run_state, executable)] = executable

                if not futures:
                    if pending:
                        unresolved = ", ".join(sorted(pending))
                        raise AuditExecutionError(f"no runnable audit tasks remain: {unresolved}")
                    break

                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    executable = futures.pop(future)
                    try:
                        future.result()
                    except Exception as exc:
                        if not executable.degrade_on_error:
                            for blocked in pending.values():
                                run_state.get_task(blocked.task.key).mark_skipped("audit aborted")
                            raise exc

    def _skip_blocked_tasks(
        self,
        run_state: AuditRunState,
        pending: dict[str, ExecutableAuditTask],
    ) -> None:
        for key, executable in list(pending.items()):
            if not executable.skip_on_failed_dependency:
                continue
            dependency_states = [run_state.get_task(dep) for dep in executable.task.dependencies]
            failed_dependency = next(
                (
                    dependency
                    for dependency in dependency_states
                    if dependency.status in {AuditTaskStatus.FAILED, AuditTaskStatus.SKIPPED}
                ),
                None,
            )
            if failed_dependency is None:
                continue
            run_state.get_task(key).mark_skipped(
                f"dependency {failed_dependency.task.key} ended as {failed_dependency.status.value}"
            )
            pending.pop(key, None)

    def _ready_executables(
        self,
        run_state: AuditRunState,
        pending: dict[str, ExecutableAuditTask],
    ) -> list[ExecutableAuditTask]:
        ready = []
        for executable in pending.values():
            if all(run_state.get_task(dep).is_terminal for dep in executable.task.dependencies):
                ready.append(executable)
        return ready

    def _execute_one(self, run_state: AuditRunState, executable: ExecutableAuditTask) -> None:
        state = run_state.get_task(executable.task.key)
        state.mark_running()
        try:
            raw_result = executable.handler(run_state)
            outcome = self._normalize_outcome(raw_result, executable)
            for section, value in outcome.sections.items():
                run_state.set_section(section, value)
            state.mark_success(result=outcome.result, summary=outcome.summary)
        except Exception as exc:
            state.mark_failed(exc)
            if not executable.degrade_on_error:
                raise

    def _normalize_outcome(
        self,
        raw_result: Any,
        executable: ExecutableAuditTask,
    ) -> AuditTaskOutcome:
        if isinstance(raw_result, AuditTaskOutcome):
            return raw_result

        summary = executable.summary_builder(raw_result) if executable.summary_builder else {}
        sections = {}
        if executable.result_section:
            sections[executable.result_section] = raw_result
        return AuditTaskOutcome(result=raw_result, summary=summary, sections=sections)
