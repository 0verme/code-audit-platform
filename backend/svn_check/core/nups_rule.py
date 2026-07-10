"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.nups_rule`."""

import sys
from audit.checks import nups_rule as _impl

sys.modules[__name__] = _impl
