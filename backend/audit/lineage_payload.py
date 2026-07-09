from __future__ import annotations

from datetime import datetime
from pathlib import Path


def json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return value.name
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    return str(value)


def empty_lineage_summary(warnings=None):
    return {
        "resultTables": [],
        "jobs": [],
        "recvPlans": [],
        "sysNames": [],
        "outfiles": [],
        "warnings": list(warnings or []),
        "stats": {},
    }


def lineage_warning(label, exc):
    return f"{label} unavailable: {type(exc).__name__}"
