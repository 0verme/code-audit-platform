"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt.ddl_rule`."""

import sys
from audit.checks.hcyt import ddl_rule as _impl

sys.modules[__name__] = _impl
