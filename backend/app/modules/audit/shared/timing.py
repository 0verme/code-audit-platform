from __future__ import annotations

import time


def run_timed(label, fn, log_timing=None, result_fields=None, **fields):
    """Run one operation and publish a consistent start/end timing pair."""

    started = time.perf_counter()
    if log_timing is not None:
        log_timing(label, "start", **fields)
    result = None
    try:
        result = fn()
        return result
    finally:
        if log_timing is not None:
            end_fields = dict(fields)
            if result_fields is not None and result is not None:
                end_fields.update(result_fields(result))
            end_fields["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
            log_timing(label, "end", **end_fields)
