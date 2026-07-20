"""Compatibility alias for HCYT DDL checks."""

import sys
from app.modules.audit.workflows.hcyt.checks import ddl_rule as _implementation

sys.modules[__name__] = _implementation
