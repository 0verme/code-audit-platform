"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.dependency`."""

import sys
from audit.checks import dependency as _impl

sys.modules[__name__] = _impl
