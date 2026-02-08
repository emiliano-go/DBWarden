class StrataError(Exception):
    """Base exception for Strata errors."""

    pass


class DirectoryNotFoundError(StrataError):
    """Raised when strata directory is not found."""

    pass


class EnvFileNotFoundError(StrataError):
    """Raised when .env file is not found."""

    pass


class ConfigurationError(StrataError):
    """Raised when there is a configuration error."""

    pass


class VersionNotFoundError(StrataError):
    """Raised when a migration version is not found."""

    pass


class PendingMigrationsError(StrataError):
    """Raised when there are pending migrations but operation requires none."""

    pass


class LockError(StrataError):
    """Raised when there is a lock error during migration."""

    pass


class DatabaseError(StrataError):
    """Raised when there is a database error."""

    pass


class NoMigrationsError(StrataError):
    """Raised when no migrations are found."""

    pass
