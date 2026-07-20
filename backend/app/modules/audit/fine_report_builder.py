"""Compatibility alias for the FineReport report builder."""

import sys
from .workflows.fine_report import report as _implementation

sys.modules[__name__] = _implementation
