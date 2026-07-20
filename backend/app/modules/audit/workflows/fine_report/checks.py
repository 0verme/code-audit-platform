"""FineReport rules compatibility boundary.

Rules remain available at their legacy import path during the compatibility
window; new workflow code imports them through this module.
"""

from app.modules.audit.checks.fine_rule import *  # noqa: F401, F403
