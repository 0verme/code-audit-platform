"""Deprecated compatibility path.

Real implementation lives in audit.checks.dependency.
Do not add new logic here.
"""

import sys
from audit.checks import dependency as _impl

sys.modules[__name__] = _impl
