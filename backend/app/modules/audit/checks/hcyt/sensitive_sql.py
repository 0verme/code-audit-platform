"""Compatibility alias for HCYT sensitive SQL checks."""

import sys
from app.modules.audit.workflows.hcyt.checks import sensitive_sql as _implementation

sys.modules[__name__] = _implementation
