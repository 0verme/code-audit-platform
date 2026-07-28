"""Explicit one-shot recovery for tasks abandoned by a stopped backend process."""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.audit_task_service import recover_orphan_tasks  # noqa: E402


if __name__ == "__main__":
    recover_orphan_tasks()
