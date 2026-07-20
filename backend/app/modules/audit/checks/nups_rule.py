"""Compatibility alias for NUPS workflow checks."""

import sys
from app.modules.audit.workflows.nups import checks as _implementation

sys.modules[__name__] = _implementation
