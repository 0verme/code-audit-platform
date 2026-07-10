"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt_rule`."""

import sys
from audit.checks import hcyt_rule as _impl

sys.modules[__name__] = _impl
