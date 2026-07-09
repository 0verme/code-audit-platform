from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class WorkflowRunContext:
    workflow: str
    svn_result: dict
    run_hcyt: Callable[[dict], dict]
    run_nups: Callable[[dict], dict]
    run_fine: Callable[[dict], dict]


def run_workflow(context: WorkflowRunContext) -> dict:
    if context.workflow == "fine-report":
        return context.run_fine(context.svn_result)
    if context.workflow == "nups":
        return context.run_nups(context.svn_result)
    return context.run_hcyt(context.svn_result)
