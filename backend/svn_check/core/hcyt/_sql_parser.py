"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt._sql_parser`."""

import sys
from audit.checks.hcyt import _sql_parser as _impl

sys.modules[__name__] = _impl
