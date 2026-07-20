"""Compatibility alias for the HCYT schedule runner."""

import sys
from .workflows.hcyt import schedule_runner as _implementation

sys.modules[__name__] = _implementation
