"""Compatibility alias for :mod:`app.modules.audit.core.dispatcher`."""

import sys
from .core import dispatcher as _implementation

sys.modules[__name__] = _implementation
