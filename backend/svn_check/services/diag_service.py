"""Deprecated compatibility path.

Real implementation lives in audit.checks.diag_service.
Do not add new logic here.
"""

import sys
from audit.checks import diag_service as _impl

sys.modules[__name__] = _impl
