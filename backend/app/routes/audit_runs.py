from flask import Blueprint, jsonify, request

from app.auth import require_permission
from app.services import ServiceError
from app.services.audit_run_service import get_partial_result, get_status
from app.services.audit_task_service import create_task
from .helpers import service_error_response

audit_runs_bp = Blueprint("audit_runs", __name__)


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "")


@audit_runs_bp.get("/api/audit-runs/<int:run_id>/status")
def status(run_id: int):
    try:
        return jsonify(get_status(run_id))
    except ServiceError as exc:
        return service_error_response(exc)


@audit_runs_bp.get("/api/audit-runs/<int:run_id>/partial-result")
def partial_result(run_id: int):
    try:
        return jsonify(get_partial_result(run_id))
    except ServiceError as exc:
        return service_error_response(exc)


@audit_runs_bp.post("/api/audit-runs")
@require_permission("audit.run.create")
def create():
    try:
        return jsonify(create_task(request.get_json(silent=True) or {}, client_ip=_client_ip())), 201
    except ServiceError as exc:
        return service_error_response(exc)
