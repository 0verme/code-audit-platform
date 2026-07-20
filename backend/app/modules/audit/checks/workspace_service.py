"""Compatibility alias for local workspace access."""

import sys
from app.modules.audit.source import workspace as _implementation

sys.modules[__name__] = _implementation
