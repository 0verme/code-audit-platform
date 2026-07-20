"""Compatibility alias for HCYT SQL parsing helpers."""

import sys
from app.modules.audit.workflows.hcyt.checks import _sql_parser as _implementation

sys.modules[__name__] = _implementation
