class MigrationError(RuntimeError):
    """Base migration failure."""


class ManifestError(MigrationError):
    """The migration manifest is missing or invalid."""


class VerificationError(MigrationError):
    """Applied migration history differs from the manifest."""
