"""Deprecated compatibility path. Real implementation lives in :mod:`audit.checks.hcyt.file_utils`."""

import sys
from audit.checks.hcyt import file_utils as _impl

sys.modules[__name__] = _impl
