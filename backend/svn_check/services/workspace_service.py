"""Deprecated compatibility path.

Real implementation lives in audit.checks.workspace_service.
Do not add new logic here.
"""

import sys
from audit.checks import workspace_service as _impl

sys.modules[__name__] = _impl
