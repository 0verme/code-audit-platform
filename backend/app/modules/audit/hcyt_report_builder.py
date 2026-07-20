"""Compatibility alias for the HCYT report builder."""

import sys
from .workflows.hcyt import report as _implementation

sys.modules[__name__] = _implementation
