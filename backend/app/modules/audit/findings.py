"""Compatibility alias for :mod:`app.modules.audit.shared.findings`."""

import sys
from .shared import findings as _implementation

sys.modules[__name__] = _implementation
