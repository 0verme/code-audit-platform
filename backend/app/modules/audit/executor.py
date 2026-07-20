"""Compatibility alias for :mod:`app.modules.audit.core.executor`."""

import sys
from .core import executor as _implementation

sys.modules[__name__] = _implementation
