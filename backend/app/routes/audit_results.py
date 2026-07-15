from flask import Blueprint, jsonify, request

from app.services.audit_result_service import get_fine_report_items, get_results

audit_results_bp = Blueprint("audit_results", __name__)


@audit_results_bp.get("/api/audit-results")
def results():
    return jsonify(get_results(request.args.get("task_id", type=int)))


@audit_results_bp.get("/api/fine-report/items")
def fine_report_items():
    return jsonify(get_fine_report_items())
