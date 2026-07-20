"""Compatibility alias for the HCYT program runner."""

import sys
from .workflows.hcyt import program_runner as _implementation

sys.modules[__name__] = _implementation
