"""Deprecated compatibility path for :mod:`metadata.services.db_service`."""

from metadata.services.db_service import *  # noqa: F401,F403
from metadata.services import db_service as _impl


def __getattr__(name):
    return getattr(_impl, name)
