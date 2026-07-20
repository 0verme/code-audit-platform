"""Compatibility alias for :mod:`app.modules.audit.core.run_state`."""

import sys
from .core import run_state as _implementation

sys.modules[__name__] = _implementation
