"""Compatibility alias for HCYT progress events."""

import sys
from .workflows.hcyt import progress as _implementation

sys.modules[__name__] = _implementation
