"""Compatibility alias for shared configured SQL reviews."""

import sys
from app.modules.audit.shared import dws_sql_review as _implementation

sys.modules[__name__] = _implementation
