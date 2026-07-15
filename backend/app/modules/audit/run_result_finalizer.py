from __future__ import annotations

from collections.abc import Callable, Sequence


def finalize_run_result(
    workflow_result: dict,
    *,
    svn_result: dict,
    source_ref: str,
    fallback_source_type: str,
    logs: Sequence[dict],
    build_source_summary: Callable[..., dict],
) -> dict:
    workflow_result.update(
        build_source_summary(
            svn_result,
            source_ref=source_ref,
            fallback_source_type=fallback_source_type,
        )
    )
    workflow_result["logs"] = logs
    return workflow_result
