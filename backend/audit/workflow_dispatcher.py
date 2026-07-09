from __future__ import annotations

from dataclasses import dataclass

from .fine_runner import run_fine
from .hcyt_runner import run_hcyt
from .nups_runner import run_nups
from .workflow_runtime import WorkflowRuntimeContext


@dataclass
class WorkflowRunContext:
    workflow: str
    runtime_context: WorkflowRuntimeContext


def run_workflow(context: WorkflowRunContext) -> dict:
    if context.workflow == "fine-report":
        return run_fine(context.runtime_context)
    if context.workflow == "nups":
        return run_nups(context.runtime_context)
    return run_hcyt(context.runtime_context)
