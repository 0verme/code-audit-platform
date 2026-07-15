import app.modules.audit.engine as audit_engine
from . import ServiceError


def get_status(run_id: int) -> dict:
    payload = audit_engine.get_audit_run_status(run_id)
    if payload is None:
        raise ServiceError("audit run not found", status_code=404)
    return payload


def get_partial_result(run_id: int) -> dict:
    payload = audit_engine.get_audit_run_partial_result(run_id)
    if payload is None:
        raise ServiceError("audit run not found", status_code=404)
    return payload
