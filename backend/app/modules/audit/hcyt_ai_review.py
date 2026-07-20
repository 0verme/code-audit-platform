"""Compatibility alias for HCYT AI review."""

import sys
from .workflows.hcyt import ai_review as _implementation

sys.modules[__name__] = _implementation
