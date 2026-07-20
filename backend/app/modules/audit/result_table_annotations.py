"""Compatibility alias for :mod:`app.modules.audit.shared.table_annotations`."""

import sys
from .shared import table_annotations as _implementation

sys.modules[__name__] = _implementation
