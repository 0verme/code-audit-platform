"""Deprecated compatibility path.

Real implementation lives in audit.checks.hcyt.file_utils.
Do not add new logic here.
"""

import sys
from audit.checks.hcyt import file_utils as _impl

sys.modules[__name__] = _impl
