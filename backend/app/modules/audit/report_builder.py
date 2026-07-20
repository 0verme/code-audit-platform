"""Compatibility alias for :mod:`app.modules.audit.shared.report_helpers`."""

import sys
from .shared import report_helpers as _implementation

sys.modules[__name__] = _implementation
