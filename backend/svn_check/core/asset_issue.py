"""Deprecated compatibility path. Real implementation lives in :mod:`audit.rules.asset_issue`."""

import sys
from audit.rules import asset_issue as _impl

sys.modules[__name__] = _impl
