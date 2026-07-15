from flask import Blueprint, jsonify

from app.services.project_service import get_projects

projects_bp = Blueprint("projects", __name__)


@projects_bp.get("/api/projects")
def projects():
    return jsonify(get_projects())
