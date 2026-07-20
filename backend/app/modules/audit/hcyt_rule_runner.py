"""Compatibility alias for the HCYT rule runner."""

import sys
from .workflows.hcyt import rule_runner as _implementation

sys.modules[__name__] = _implementation
