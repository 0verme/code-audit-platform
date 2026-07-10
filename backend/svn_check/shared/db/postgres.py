"""Deprecated compatibility path.

Real implementation lives in db.metadata.compat.postgres.
Do not add new logic here.
"""

import sys
from db.metadata.compat import postgres as _impl

sys.modules[__name__] = _impl
