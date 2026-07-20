"""Compatibility alias for :mod:`app.modules.audit.shared.lineage_overlay`."""

import sys
from .shared import lineage_overlay as _implementation

sys.modules[__name__] = _implementation
