"""Compatibility alias for the SVN source adapter."""

import sys
from app.modules.audit.source import svn as _implementation

sys.modules[__name__] = _implementation
