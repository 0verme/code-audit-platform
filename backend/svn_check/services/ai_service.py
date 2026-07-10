"""Deprecated compatibility path.

Real implementation lives in audit.checks.ai_service.
Do not add new logic here.
"""

import sys
from audit.checks import ai_service as _impl

sys.modules[__name__] = _impl
