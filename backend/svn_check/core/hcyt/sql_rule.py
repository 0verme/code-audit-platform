"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt.sql_rule`."""

import sys
from audit.checks.hcyt import sql_rule as _impl

sys.modules[__name__] = _impl
