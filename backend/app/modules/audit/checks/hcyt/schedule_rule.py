"""Compatibility alias for HCYT schedule checks."""

import sys
from app.modules.audit.workflows.hcyt.checks import schedule_rule as _implementation

sys.modules[__name__] = _implementation
