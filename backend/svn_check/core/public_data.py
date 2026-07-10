"""Deprecated compatibility path. Real implementation lives in :mod:`metadata.services.public_data`."""

import sys
from metadata.services import public_data as _impl

sys.modules[__name__] = _impl
