from __future__ import annotations


def run_workflow(
    workflow: str,
    svn_result: dict,
    *,
    run_hcyt,
    run_nups,
    run_fine,
) -> dict:
    if workflow == "fine-report":
        return run_fine(svn_result)
    if workflow == "nups":
        return run_nups(svn_result)
    return run_hcyt(svn_result)
