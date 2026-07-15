from __future__ import annotations

from functools import wraps


def require_permission(_permission: str):
    """Extension point for authorization; permissive until an identity provider is configured."""
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator
