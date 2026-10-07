"""HTTP blueprints for the audit platform."""

from .audit_results import audit_results_bp
from .audit_configuration import audit_configuration_bp
from .audit_runs import audit_runs_bp
from .audit_tasks import audit_tasks_bp
from .health import health_bp
from .projects import projects_bp
from .publish_list import publish_list_bp
from .rule_catalog import rule_catalog_bp

BLUEPRINTS = (
    health_bp,
    projects_bp,
    audit_tasks_bp,
    audit_runs_bp,
    audit_results_bp,
    audit_configuration_bp,
    publish_list_bp,
    rule_catalog_bp,
)

__all__ = ["BLUEPRINTS"]
