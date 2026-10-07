"""Read-only API for the static audit rule catalog."""
from flask import Blueprint, abort, jsonify, request

from app.modules.audit.rules.registry import rule_inventory

rule_catalog_bp = Blueprint("rule_catalog", __name__)


@rule_catalog_bp.get("/api/rules")
def list_rules():
    rules = list(rule_inventory())
    workflow = request.args.get("workflow", "").strip().casefold()
    category = request.args.get("category", "").strip().casefold()
    severity = request.args.get("severity", "").strip().casefold()
    keyword = request.args.get("keyword", "").strip().casefold()

    if workflow:
        rules = [rule for rule in rules if rule["workflow"].casefold() == workflow]
    if category:
        rules = [rule for rule in rules if rule["category"].casefold() == category]
    if severity:
        rules = [rule for rule in rules if rule["severity"].casefold() == severity]
    if keyword:
        searchable_fields = ("id", "title", "description")
        rules = [
            rule for rule in rules
            if any(keyword in rule[field].casefold() for field in searchable_fields)
        ]

    return jsonify(rules)


@rule_catalog_bp.get("/api/rules/<string:rule_id>")
def rule_detail(rule_id: str):
    rule = next((item for item in rule_inventory() if item["id"] == rule_id), None)
    if rule is None:
        abort(404)
    return jsonify(rule)
