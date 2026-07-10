"""Deprecated compatibility path.

Real implementation lives in db.metadata.compat.router.
Do not add new logic here.
"""

import sys
from db.metadata.compat import router as _impl

sys.modules[__name__] = _impl
