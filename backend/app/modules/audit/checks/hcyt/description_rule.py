"""Compatibility alias for HCYT description checks."""

import sys
from app.modules.audit.workflows.hcyt.checks import description_rule as _implementation

sys.modules[__name__] = _implementation
