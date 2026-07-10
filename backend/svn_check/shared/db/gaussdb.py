"""Deprecated compatibility path.

Real implementation lives in db.metadata.compat.gaussdb.
Do not add new logic here.
"""

import sys
from db.metadata.compat import gaussdb as _impl

sys.modules[__name__] = _impl
