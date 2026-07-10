"""Deprecated compatibility path.

Real implementation lives in audit.checks.hcyt_rule.
Do not add new logic here.
"""

import sys
from audit.checks import hcyt_rule as _impl

sys.modules[__name__] = _impl
