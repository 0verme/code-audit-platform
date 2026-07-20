"""Compatibility alias for audit diagnostics."""

import sys
from app.modules.audit.integrations import diagnostics as _implementation

sys.modules[__name__] = _implementation
