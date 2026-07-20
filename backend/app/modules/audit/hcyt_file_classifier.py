"""Compatibility alias for HCYT input classification."""

import sys
from .workflows.hcyt import classifier as _implementation

sys.modules[__name__] = _implementation
