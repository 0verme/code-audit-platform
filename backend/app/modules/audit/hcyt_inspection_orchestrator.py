"""Compatibility alias for HCYT inspection orchestration."""

import sys
from .workflows.hcyt import orchestrator as _implementation

sys.modules[__name__] = _implementation
