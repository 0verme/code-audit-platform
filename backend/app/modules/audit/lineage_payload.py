"""Compatibility alias for :mod:`app.modules.audit.shared.lineage_payload`."""

import sys
from .shared import lineage_payload as _implementation

sys.modules[__name__] = _implementation
