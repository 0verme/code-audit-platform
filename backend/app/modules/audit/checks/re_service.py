"""Compatibility alias for shared file analysis helpers."""

import sys
from app.modules.audit.shared import file_analysis as _implementation

sys.modules[__name__] = _implementation
