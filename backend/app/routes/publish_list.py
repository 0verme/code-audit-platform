from datetime import date

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

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
