"""Compatibility alias for the FineReport workflow runner."""

import sys
from .workflows.fine_report import runner as _implementation

sys.modules[__name__] = _implementation
