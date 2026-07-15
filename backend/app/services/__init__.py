"""Application services independent from Flask HTTP objects."""


class ServiceError(Exception):
    """An expected service failure with a backwards-compatible HTTP payload."""

    def __init__(self, message: str, *, status_code: int, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {"error": message}
