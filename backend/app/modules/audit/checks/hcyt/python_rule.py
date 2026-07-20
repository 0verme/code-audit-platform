"""Compatibility alias for HCYT Python checks."""

import sys
from app.modules.audit.workflows.hcyt.checks import python_rule as _implementation

sys.modules[__name__] = _implementation
