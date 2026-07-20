"""Compatibility alias for :mod:`app.modules.audit.core.run_registry`."""

import sys
from .core import run_registry as _implementation

sys.modules[__name__] = _implementation
