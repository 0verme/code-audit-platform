"""Compatibility alias for the NUPS workflow runner."""

import sys
from .workflows.nups import runner as _implementation

sys.modules[__name__] = _implementation
