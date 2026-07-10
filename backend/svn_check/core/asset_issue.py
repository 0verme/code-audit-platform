"""Deprecated compatibility path.

Real implementation lives in audit.rules.asset_issue.
Do not add new logic here.
"""

import sys
from audit.rules import asset_issue as _impl

sys.modules[__name__] = _impl
