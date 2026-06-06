class DBWardenError(Exception):
    """Base exception for DBWarden errors."""

    pass


class DirectoryNotFoundError(DBWardenError):
    """Raised when migrations directory is not found."""

    pass


class ConfigurationError(DBWardenError):
    """Raised when there is a configuration error."""

    pass


class VersionNotFoundError(DBWardenError):
    """Raised when a migration version is not found."""

    pass


class PendingMigrationsError(DBWardenError):
    """Raised when there are pending migrations but operation requires none."""

    pass


class LockError(DBWardenError):
    """Raised when there is a lock error during migration."""

    pass


class DatabaseError(DBWardenError):
    """Raised when there is a database error."""

    pass


class NoMigrationsError(DBWardenError):
    """Raised when no migrations are found."""

    pass


class SeedError(DBWardenError):
    """Raised when there is a seed-related error."""

    pass


class NoSeedsError(DBWardenError):
    """Raised when no seeds are found."""

    pass
