"""Compatibility alias for :mod:`app.modules.audit.shared.issue_adapter`."""

import sys
from .shared import issue_adapter as _implementation

sys.modules[__name__] = _implementation
