"""Compatibility alias for :mod:`app.modules.audit.core.failure_result`."""

import sys
from .core import failure_result as _implementation

sys.modules[__name__] = _implementation
