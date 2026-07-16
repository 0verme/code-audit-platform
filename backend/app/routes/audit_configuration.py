"""Read-only, non-secret audit configuration for frontend prechecks."""
import logging

from flask import Blueprint, jsonify

from app.config.audit_rules import get_audit_rules
from app.modules.audit.checks.svn_service import load_svn_config

audit_configuration_bp = Blueprint("audit_configuration", __name__)
LOGGER = logging.getLogger(__name__)


def _svn_source_display_rules() -> list[dict[str, str]]:
    """Derive display-only prefixes without exposing SVN credentials."""
    try:
        projects = load_svn_config().get("projects", {})
    except Exception as exc:
        LOGGER.warning("SVN source display rules unavailable: %s", type(exc).__name__)
        return []

    rules = []
    seen_prefixes = set()
    for project in projects.values():
        if not isinstance(project, dict):
            continue
        trunk_url = str(project.get("trunk_url") or "").strip().rstrip("/")
        normalized_prefix = trunk_url.lower()
        if not trunk_url or normalized_prefix in seen_prefixes:
            continue
        seen_prefixes.add(normalized_prefix)
        rules.append({
            "sourceType": "svn",
            "prefix": f"{trunk_url}/",
            "replacement": "…/",
        })
    return rules


@audit_configuration_bp.get("/api/audit-configuration/workflows")
def workflows():
    rules = get_audit_rules()
    workflows = rules.get("workflows", {})
    definitions = workflows.get("definitions", [])
    source_display_rules = list(rules.get("source_display_rules", []))
    source_display_rules.extend(_svn_source_display_rules())
    return jsonify({
        "default": workflows.get("default", "hcyt"),
        "definitions": definitions,
        "sourceDisplayRules": source_display_rules,
    })
