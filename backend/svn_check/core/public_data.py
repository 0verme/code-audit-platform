"""Deprecated compatibility path.

Real implementation lives in metadata.services.public_data.
Do not add new logic here.
"""

import sys
from metadata.services import public_data as _impl

sys.modules[__name__] = _impl
