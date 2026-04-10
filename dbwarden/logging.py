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
    for migration operations with database context.
    """

    def __init__(
        self,
        name: str = "dbwarden",
        verbose: bool = False,
        db_name: str | None = None,
        db_type: str | None = None,
    ):
        """
        Initialize the DBWarden logger.

        Args:
            name: Logger name (default: "dbwarden")
            verbose: If True, sets level to DEBUG; otherwise INFO.
            db_name: Database name from multi-db config.
            db_type: Database type (sqlite, postgresql, mysql, mariadb, clickhouse).
        """
        self.logger = logging.getLogger(name)
        self.verbose = verbose
        self.db_name = db_name
        self.db_type = db_type
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

    def _format_db_context(self) -> str:
        """Format database context for log messages."""
        if self.db_name and self.db_type:
            return f"[{self.db_name}/{self.db_type}]"
        elif self.db_name:
            return f"[{self.db_name}]"
        elif self.db_type:
            return f"[{self.db_type}]"
        return ""

    def log_connection_init(self, db_type: str | None = None) -> None:
        """Log database connection initialization."""
        if db_type:
            self.db_type = db_type
        ctx = self._format_db_context()
        self.info(f"Database connection initialized: {ctx}")

    def log_pending_migrations(self, migrations: list[str]) -> None:
        """Log list of pending migrations."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        if migrations:
            self.info(f"{prefix}Pending migrations ({len(migrations)}):")
            for m in migrations:
                self.info(f"  {colorize_status('PENDING')} {m}")

    def log_migration_start(self, version: str, filename: str) -> None:
        """Log migration start."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(f"{prefix}Starting migration: {filename} (version: {version})")

    def log_migration_end(self, version: str, filename: str, duration: float) -> None:
        """Log migration end with duration."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(
            f"{prefix}{colorize_status('APPLIED')} Completed migration: {filename} (version: {version}) in {duration:.2f}s"
        )

    def log_rollback_start(self, version: str, filename: str) -> None:
        """Log rollback start."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(f"{prefix}Rolling back migration: {filename} (version: {version})")

    def log_rollback_end(self, version: str, filename: str, duration: float) -> None:
        """Log rollback end with duration."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(
            f"{prefix}{colorize_status('ROLLED_BACK')} Rollback completed: {filename} (version: {version}) in {duration:.2f}s"
        )

    def log_sql_statement(self, sql: str) -> None:
        """Log SQL statement with syntax highlighting (verbose only)."""
        if self.verbose:
            highlighted = colorize_sql(sql)
            ctx = self._format_db_context()
            prefix = f"{ctx} " if ctx else ""
            self.debug(f"{prefix}SQL Statement:\n{highlighted}")

    def log_backup_created(self, backup_path: str) -> None:
        """Log backup creation."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(f"{prefix}{colorize_status('APPLIED')} Backup created: {backup_path}")

    def log_baseline_set(self, version: str) -> None:
        """Log baseline migration set."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(
            f"{prefix}{colorize_status('APPLIED')} Baseline set at version: {version}"
        )

    def log_seed_migration(self, filename: str) -> None:
        """Log seed migration."""
        ctx = self._format_db_context()
        prefix = f"{ctx} " if ctx else ""
        self.info(f"{prefix}{colorize_status('APPLIED')} Seed data applied: {filename}")

    def log_model_discovered(self, table_name: str, columns: list) -> None:
        """Log model discovered from SQLAlchemy models (verbose only)."""
        if self.verbose:
            ctx = self._format_db_context()
            prefix = f"{ctx} " if ctx else ""
            self.debug(
                f"{prefix}Discovered model: {table_name} with {len(columns)} columns"
            )

    def log_model_paths(self, paths: list[str]) -> None:
        """Log model paths being used (verbose only)."""
        if self.verbose:
            ctx = self._format_db_context()
            prefix = f"{ctx} " if ctx else ""
            self.debug(f"{prefix}Using model paths: {paths}")

    def log_table_columns(self, table_name: str, columns: list) -> None:
        """Log table columns (verbose only)."""
        if self.verbose:
            ctx = self._format_db_context()
            prefix = f"{ctx} " if ctx else ""
            col_info = ", ".join(c["name"] for c in columns)
            self.debug(f"{prefix}Table {table_name} columns: {col_info}")

    def log_migration_sql_gen(self, table_name: str, sql: str) -> None:
        """Log generated migration SQL (verbose only)."""
        if self.verbose:
            highlighted = colorize_sql(sql)
            ctx = self._format_db_context()
            prefix = f"{ctx} " if ctx else ""
            self.debug(f"{prefix}Generated SQL for {table_name}:\n{highlighted}")


_global_logger: Optional[DBWardenLogger] = None


def get_logger(
    verbose: bool = False,
    db_name: str | None = None,
    db_type: str | None = None,
) -> DBWardenLogger:
    """
    Get the global DBWarden logger instance.

    Args:
        verbose: If True, sets logger to DEBUG level.
        db_name: Database name from multi-db config.
        db_type: Database type (sqlite, postgresql, mysql, mariadb, clickhouse).

    Returns:
        DBWardenLogger: The global logger instance.
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = DBWardenLogger(
            verbose=verbose, db_name=db_name, db_type=db_type
        )
    else:
        if _global_logger.verbose != verbose:
            _global_logger.set_verbose(verbose)
        if db_name is not None:
            _global_logger.db_name = db_name
        if db_type is not None:
            _global_logger.db_type = db_type
    return _global_logger


def reset_logger() -> None:
    """Reset the global logger instance."""
    global _global_logger
    _global_logger = None
