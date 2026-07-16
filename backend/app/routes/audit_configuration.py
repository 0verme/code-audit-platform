"""Read-only, non-secret audit configuration for frontend prechecks."""
from flask import Blueprint, jsonify

from app.config.audit_rules import get_audit_rules

audit_configuration_bp = Blueprint("audit_configuration", __name__)


@audit_configuration_bp.get("/api/audit-configuration/workflows")
def workflows():
    rules = get_audit_rules()
    workflows = rules.get("workflows", {})
    definitions = workflows.get("definitions", [])
    return jsonify({"default": workflows.get("default", "hcyt"), "definitions": definitions})
