"""Compatibility alias for :mod:`app.modules.audit.source.resolver`."""

import sys
from .source import resolver as _implementation

sys.modules[__name__] = _implementation
