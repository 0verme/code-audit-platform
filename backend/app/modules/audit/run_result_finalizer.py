"""Compatibility alias for :mod:`app.modules.audit.core.result_finalizer`."""

import sys
from .core import result_finalizer as _implementation

sys.modules[__name__] = _implementation
