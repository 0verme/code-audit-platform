class DatabaseError(RuntimeError):
    """Base error for database profile connection and execution failures."""


class DatabaseDriverError(DatabaseError):
    """Raised when a required database driver is not installed."""


class SqlExecutionError(DatabaseError):
    """Raised when SQL execution fails."""
