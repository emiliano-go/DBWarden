import logging
import sys
from typing import Optional

from dbwarden.constants import LOG_FORMAT


class DBWardenLogger:
    """
    Structured logging for DBWarden operations.

    Provides configurable logging levels and structured output
    for migration operations.
    """

    def __init__(self, name: str = "dbwarden", verbose: bool = False):
        """
        Initialize the DBWarden logger.

        Args:
            name: Logger name (default: "dbwarden")
            verbose: If True, sets level to DEBUG; otherwise INFO.
        """
        self.logger = logging.getLogger(name)
        self.verbose = verbose
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure the logger with appropriate handlers and level."""
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
            formatter = logging.Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def set_verbose(self, verbose: bool) -> None:
        """
        Update verbosity level.

        Args:
            verbose: New verbosity setting.
        """
        self.verbose = verbose
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        for handler in self.logger.handlers:
            handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    def debug(self, msg: str, **kwargs) -> None:
        """Log a debug message."""
        self.logger.debug(msg, extra=kwargs)

    def info(self, msg: str, **kwargs) -> None:
        """Log an info message."""
        self.logger.info(msg, extra=kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        """Log a warning message."""
        self.logger.warning(msg, extra=kwargs)

    def error(self, msg: str, **kwargs) -> None:
        """Log an error message."""
        self.logger.error(msg, extra=kwargs)

    def critical(self, msg: str, **kwargs) -> None:
        """Log a critical message."""
        self.logger.critical(msg, extra=kwargs)

    def log_execution_mode(self, mode: str) -> None:
        """Log detected execution mode."""
        self.info(f"Detected execution mode: {mode}")

    def log_connection_init(self, db_type: str) -> None:
        """Log database connection initialization."""
        self.info(f"Database connection initialized: {db_type}")

    def log_pending_migrations(self, migrations: list[str]) -> None:
        """Log list of pending migrations."""
        if migrations:
            self.info(f"Pending migrations ({len(migrations)}):")
            for m in migrations:
                self.info(f"  - {m}")

    def log_migration_start(self, version: str, filename: str) -> None:
        """Log migration start."""
        self.info(f"Starting migration: {filename} (version: {version})")

    def log_migration_end(self, version: str, filename: str, duration: float) -> None:
        """Log migration end with duration."""
        self.info(
            f"Completed migration: {filename} (version: {version}) in {duration:.2f}s"
        )

    def log_sql_statement(self, sql: str) -> None:
        """Log SQL statement (verbose only)."""
        self.debug(f"SQL Statement: {sql}")


_global_logger: Optional[DBWardenLogger] = None


def get_logger(verbose: bool = False) -> DBWardenLogger:
    """
    Get the global DBWarden logger instance.

    Args:
        verbose: If True, sets logger to DEBUG level.

    Returns:
        DBWardenLogger: The global logger instance.
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = DBWardenLogger(verbose=verbose)
    elif _global_logger.verbose != verbose:
        _global_logger.set_verbose(verbose)
    return _global_logger


def reset_logger() -> None:
    """Reset the global logger instance."""
    global _global_logger
    _global_logger = None
