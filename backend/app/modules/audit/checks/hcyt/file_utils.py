"""Compatibility alias for HCYT file helpers."""

import sys
from app.modules.audit.workflows.hcyt.checks import file_utils as _implementation

sys.modules[__name__] = _implementation
