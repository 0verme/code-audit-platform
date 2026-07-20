"""Compatibility alias for the NUPS report builder."""

import sys
from .workflows.nups import report as _implementation

sys.modules[__name__] = _implementation
