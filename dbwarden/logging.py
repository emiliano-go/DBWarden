import logging
import re
import sys
from typing import Optional

from dbwarden.constants import LOG_FORMAT

ANSI_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bg_red": "\033[41m",
    "bg_green": "\033[42m",
}

STATUS_COLORS = {
    "PENDING": ANSI_COLORS["yellow"],
    "APPLIED": ANSI_COLORS["green"],
    "ROLLED_BACK": ANSI_COLORS["red"],
    "FAILED": ANSI_COLORS["red"],
    "RUNNING": ANSI_COLORS["blue"],
    "SKIPPED": ANSI_COLORS["dim"] + ANSI_COLORS["yellow"],
}

LOG_COLORS = {
    logging.DEBUG: ANSI_COLORS["dim"] + ANSI_COLORS["cyan"],
    logging.INFO: ANSI_COLORS["reset"],
    logging.WARNING: ANSI_COLORS["yellow"],
    logging.ERROR: ANSI_COLORS["red"],
    logging.CRITICAL: ANSI_COLORS["bold"] + ANSI_COLORS["red"],
}


def supports_color() -> bool:
    """Check if the terminal supports ANSI colors."""
    return sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Wrap text with ANSI color codes."""
    if not supports_color():
        return text
    return f"{color}{text}{ANSI_COLORS['reset']}"


def colorize_status(status: str) -> str:
    """Colorize a status string with appropriate color."""
    color = STATUS_COLORS.get(status.upper(), ANSI_COLORS["reset"])
    return colorize(f"[{status.upper()}]", color)


SQL_KEYWORDS = [
    "CREATE",
    "TABLE",
    "INDEX",
    "VIEW",
    "DROP",
    "ALTER",
    "INSERT",
    "UPDATE",
    "DELETE",
    "SELECT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "ORDER",
    "BY",
    "GROUP",
    "HAVING",
    "LIMIT",
    "OFFSET",
    "PRIMARY",
    "KEY",
    "FOREIGN",
    "REFERENCES",
    "NOT",
    "NULL",
    "UNIQUE",
    "CHECK",
    "DEFAULT",
    "CONSTRAINT",
    "IF",
    "EXISTS",
    "BEGIN",
    "COMMIT",
    "ROLLBACK",
    "TRANSACTION",
    "VALUES",
    "SET",
    "AS",
    "IN",
    "IS",
    "LIKE",
    "BETWEEN",
    "CAST",
    "UNION",
    "ALL",
    "DISTINCT",
    "ASC",
    "DESC",
    "INTO",
    "TEMPORARY",
    "INTEGER",
    "VARCHAR",
    "TEXT",
    "BOOLEAN",
    "DATETIME",
    "FLOAT",
    "DATE",
    "JSON",
    "SERIAL",
    "BIGINT",
    "SMALLINT",
    "NUMERIC",
]


def colorize_sql(sql: str) -> str:
    """Apply basic SQL syntax highlighting."""
    if not supports_color():
        return sql

    result = sql

    for keyword in SQL_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        result = re.sub(
            pattern,
            lambda m: colorize(m.group(0), ANSI_COLORS["magenta"]),
            result,
            flags=re.IGNORECASE,
        )

    result = re.sub(
        r"'[^']*'",
        lambda m: colorize(m.group(0), ANSI_COLORS["green"]),
        result,
    )

    result = re.sub(
        r"--.*$",
        lambda m: colorize(m.group(0), ANSI_COLORS["dim"] + ANSI_COLORS["cyan"]),
        result,
        flags=re.MULTILINE,
    )

    return result


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log output."""

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelno
        color = LOG_COLORS.get(level, ANSI_COLORS["reset"])

        msg = record.getMessage()

        if not supports_color():
            return super().format(record)

        record.msg = colorize(msg, color)

        return super().format(record)


class DBWardenLogger:
    """
    Structured logging for DBWarden operations.

    Provides configurable logging levels and colored output
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

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        colored_formatter = ColoredFormatter(LOG_FORMAT)
        handler.setFormatter(colored_formatter)
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
                self.info(f"  {colorize_status('PENDING')} {m}")

    def log_migration_start(self, version: str, filename: str) -> None:
        """Log migration start."""
        self.info(f"Starting migration: {filename} (version: {version})")

    def log_migration_end(self, version: str, filename: str, duration: float) -> None:
        """Log migration end with duration."""
        self.info(
            f"{colorize_status('APPLIED')} Completed migration: {filename} (version: {version}) in {duration:.2f}s"
        )

    def log_rollback_start(self, version: str, filename: str) -> None:
        """Log rollback start."""
        self.info(f"Rolling back migration: {filename} (version: {version})")

    def log_rollback_end(self, version: str, filename: str, duration: float) -> None:
        """Log rollback end with duration."""
        self.info(
            f"{colorize_status('ROLLED_BACK')} Rollback completed: {filename} (version: {version}) in {duration:.2f}s"
        )

    def log_sql_statement(self, sql: str) -> None:
        """Log SQL statement with syntax highlighting (verbose only)."""
        if self.verbose:
            highlighted = colorize_sql(sql)
            self.debug(f"SQL Statement:\n{highlighted}")

    def log_backup_created(self, backup_path: str) -> None:
        """Log backup creation."""
        self.info(f"{colorize_status('APPLIED')} Backup created: {backup_path}")

    def log_baseline_set(self, version: str) -> None:
        """Log baseline migration set."""
        self.info(f"{colorize_status('APPLIED')} Baseline set at version: {version}")

    def log_seed_migration(self, filename: str) -> None:
        """Log seed migration."""
        self.info(f"{colorize_status('APPLIED')} Seed data applied: {filename}")


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
