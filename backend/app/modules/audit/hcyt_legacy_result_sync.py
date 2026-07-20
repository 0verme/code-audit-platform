"""Compatibility alias for HCYT legacy result synchronization."""

import sys
from .workflows.hcyt import legacy_sync as _implementation

sys.modules[__name__] = _implementation
