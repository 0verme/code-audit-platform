from datetime import date

from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import BadRequest

from app.auth import require_permission
from app.services.publish_list_export_service import build_publish_list_workbook
from app.services.publish_list_service import get_publish_list


publish_list_bp = Blueprint("publish_list", __name__)


@publish_list_bp.get("/api/publish-list")
def publish_list():
    raw_date = request.args.get("date", "")
    try:
        selected_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise BadRequest("date must use YYYY-MM-DD") from exc
    return jsonify(get_publish_list(selected_date))


@publish_list_bp.get("/api/publish-list/export")
@require_permission("publish-list.export")
def export_publish_list():
    raw_date = request.args.get("date", "")
    try:
        selected_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise BadRequest("date must use YYYY-MM-DD") from exc

    status = request.args.get("status") or None
    requirement_types = request.args.getlist("type")
    try:
        workbook = build_publish_list_workbook(
            selected_date,
            status=status,
            requirement_types=requirement_types,
        )
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    return send_file(
        workbook,
        as_attachment=True,
        download_name=f"上线清单_{selected_date.isoformat()}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
