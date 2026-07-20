"""Compatibility alias for the HCYT workflow runner."""

import sys
from .workflows.hcyt import runner as _implementation

sys.modules[__name__] = _implementation
