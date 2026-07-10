"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt.python_rule`."""

import sys
from audit.checks.hcyt import python_rule as _impl

sys.modules[__name__] = _impl
