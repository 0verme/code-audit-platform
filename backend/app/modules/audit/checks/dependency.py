"""Compatibility alias for shared dependency graph helpers."""

import sys
from app.modules.audit.shared import dependency as _implementation

sys.modules[__name__] = _implementation
