"""Compatibility alias for the AI integration."""

import sys
from app.modules.audit.integrations import ai as _implementation

sys.modules[__name__] = _implementation
