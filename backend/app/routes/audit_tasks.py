from flask import Blueprint, Response, jsonify, request, send_file

from app.auth import require_permission
from app.services import ServiceError
from app.services.audit_task_service import create_task, get_report_json, get_task, get_tasks
from app.services.source_file_service import resolve_source_file
from app.services.lineage_service import get_task_lineage_subgraph
from .helpers import service_error_response

audit_tasks_bp = Blueprint("audit_tasks", __name__)


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "")


@audit_tasks_bp.get("/api/audit-tasks")
def list_tasks():
    return jsonify(get_tasks())


@audit_tasks_bp.get("/api/audit-tasks/<int:task_id>")
def task_detail(task_id: int):
    try:
        return jsonify(get_task(task_id))
    except ServiceError as exc:
        return service_error_response(exc)


@audit_tasks_bp.get("/api/audit-tasks/<int:task_id>/report")
def task_report(task_id: int):
    try:
        return Response(get_report_json(task_id), mimetype="application/json")
    except ServiceError as exc:
        return service_error_response(exc)


@audit_tasks_bp.get("/api/audit-tasks/<int:task_id>/source-file")
@require_permission("audit.source.download")
def source_file(task_id: int):
    try:
        path = resolve_source_file(task_id, request.args.get("path", ""))
        return send_file(path, as_attachment=True, download_name=path.name)
    except ServiceError as exc:
        return service_error_response(exc)


@audit_tasks_bp.get("/api/audit-tasks/<int:task_id>/lineage/subgraph")
def task_lineage_subgraph(task_id: int):
    try:
        return jsonify(get_task_lineage_subgraph(
            task_id,
            request.args.get("rootKey"),
        ))
    except ServiceError as exc:
        return service_error_response(exc)


@audit_tasks_bp.post("/api/audit-tasks")
@require_permission("audit.task.create")
def create():
    try:
        result = create_task(
            request.get_json(silent=True) or {},
            client_ip=_client_ip(),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return jsonify(result), 200 if result["deduplicated"] else 201
    except ServiceError as exc:
        return service_error_response(exc)
