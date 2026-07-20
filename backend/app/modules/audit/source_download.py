"""Compatibility alias for :mod:`app.modules.audit.source.download`."""

import sys
from .source import download as _implementation

sys.modules[__name__] = _implementation
