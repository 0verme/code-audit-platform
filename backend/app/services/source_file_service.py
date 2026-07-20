import json

import app.modules.audit.engine as audit_engine
from app.db.runtime_store import get_audit_task, get_task_report_row
from app.modules.audit.source.download import resolve_source_download_path
from . import ServiceError


def resolve_source_file(task_id: int, relative_path: str):
    task = get_audit_task(task_id)
    report_row = get_task_report_row(task_id)
    if task is None or report_row is None:
        raise ServiceError("audit task or report not found", status_code=404)
    try:
        report = json.loads(report_row["report_json"])
        re_service = getattr(audit_engine._mods, "re_service", None) or __import__(
            "app.modules.audit.checks.re_service", fromlist=["get_export_base"]
        )
        return resolve_source_download_path(
            task=dict(task), report=report, relative_path=relative_path, export_base=re_service.get_export_base()
        )
    except ValueError as exc:
        raise ServiceError(str(exc), status_code=400) from exc
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ServiceError(str(exc) or "source file not found", status_code=404) from exc
