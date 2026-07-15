from flask import Blueprint, jsonify

from app.services.health_service import get_health

health_bp = Blueprint("health", __name__)


@health_bp.get("/api/health")
def health():
    payload, status = get_health()
    return jsonify(payload), status
