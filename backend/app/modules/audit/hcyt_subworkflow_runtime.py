"""Compatibility alias for the HCYT subworkflow runtime."""

import sys
from .workflows.hcyt import subworkflow_runtime as _implementation

sys.modules[__name__] = _implementation
