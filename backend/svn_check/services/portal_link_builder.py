"""Deprecated compatibility path. Real implementation lives in :mod:`audit.rules.portal_link_builder`."""

import sys
from audit.rules import portal_link_builder as _impl

sys.modules[__name__] = _impl
