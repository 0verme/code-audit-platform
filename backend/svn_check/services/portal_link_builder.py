"""Deprecated compatibility path.

Real implementation lives in audit.rules.portal_link_builder.
Do not add new logic here.
"""

import sys
from audit.rules import portal_link_builder as _impl

sys.modules[__name__] = _impl
