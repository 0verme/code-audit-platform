"""Compatibility alias for :mod:`app.modules.audit.shared.result_normalizer`."""

import sys
from .shared import result_normalizer as _implementation

sys.modules[__name__] = _implementation
