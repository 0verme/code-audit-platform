"""Deprecated compatibility path.

Real implementation lives in audit.checks.hcyt._sql_parser.
Do not add new logic here.
"""

import sys
from audit.checks.hcyt import _sql_parser as _impl

sys.modules[__name__] = _impl
