"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.fine_rule`."""

import sys
from audit.checks import fine_rule as _impl

sys.modules[__name__] = _impl
