"""Deprecated compatibility path.

Real implementation lives in metadata.services.audit_metadata_service.
Do not add new logic here.
"""

from metadata.services.audit_metadata_service import *  # noqa: F401,F403
from metadata.services import audit_metadata_service as _impl


def __getattr__(name):
    return getattr(_impl, name)
