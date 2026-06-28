"""
Logging utilities with severity-based levels and configurable verbosity.

This module builds on Python's standard logging library rather than modifying it. Standard logging levels DEBUG, INFO, WARNING, ERROR, and CRITICAL continue to represent message severity.

In addition to severity, this module introduces a seperate verbosity concept for user-facing INFO output. Verbosity controls how much detail is emitted without changing the semantic meaning of standard logging levels.

The supported verbosity levels are:
    QUIET: Emit only essential INFO messages and details.
    NORMAL: Emit standard INFO progress messages.
    VERBOSE: Emit additional explanatory or diagnostic informational messages.

This seperation allows callers to distinguish between dev diagnostics (DEBUG) and detailed user-facing output (INFO gated by verbosity).

Verbosity may be configured from multiple sources, such as constructor arguments, config files, env vars, or CLI options.

"""

import json
import logging
import os
import re
import sys
from typing import Any, Optional
from enum import IntEnum
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from dbwarden.constants import LOG_FORMAT


class Verbosity(IntEnum):
    QUIET = 0
    NORMAL = 1
    VERBOSE = 2


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

    result = re.sub(
        r"\b(" + "|".join(re.escape(keyword) for keyword in SQL_KEYWORDS) + r")\b",
        lambda m: colorize(m.group(0), ANSI_COLORS["magenta"]),
        sql,
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


class JSONFormatter(logging.Formatter):
    """Formats log records as newline-delimited JSON objects.

    Activated when the ``DBWARDEN_LOG_JSON`` environment variable is set.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "db_name") and record.db_name:
            payload["db_name"] = record.db_name
        if hasattr(record, "db_type") and record.db_type:
            payload["db_type"] = record.db_type
        if (
            record.exc_info
            and isinstance(record.exc_info, tuple)
            and record.exc_info[0]
        ):
            payload["exception"] = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text
        return json.dumps(payload, default=str)


def _use_json_logging() -> bool:
    return os.environ.get("DBWARDEN_LOG_JSON", "false").lower() in (
        "true",
        "1",
        "yes",
    )


LogMessage = Callable[[], str]

@dataclass(frozen=True)
class LogCandidate:
    """Candidate log entry keyed by a stdlib Python logging level.

    log_severity_level intentionally uses int because Python's logging
    module defines levels like logging.DEBUG and logging.INFO as integer
    constants. Storing the raw stdlib level keeps this class directly
    compatible with logging APIs and avoids wrapping or translating
    those values through a separate enum.
    """

    log_severity_level: int
    message_factory: LogMessage
    log_verbosity_level: Verbosity = Verbosity.NORMAL


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
        debug_enabled: bool = False,
        verbosity: Verbosity = Verbosity.NORMAL,
        db_name: str | None = None,
        db_type: str | None = None,
    ) -> None:
        """
        Initialize the DBWarden logger.

        Args:
            name: Logger name (default: "dbwarden")
            verbose: Only here to support current behavior until I learn enough rope to delete the class attribute across the codebase
            debug_enabled: switches between log.level == log.DEBUG if true and log.level == log.INFO if false
            verbosity: Enum that determines between the three different INFO logging verbosity settings
            db_name: Database name from multi-db config.
            db_type: Database type (sqlite, postgresql, mysql, mariadb, clickhouse).
        """
        self.logger = logging.getLogger(name)
        self.verbose = verbose
        self.debug_enabled = debug_enabled

        if not isinstance(verbosity, Verbosity):
            raise TypeError(
                f"verbosity must be a Verbosity member, got {type(verbosity)}"
            )

        self.verbosity = verbosity
        self.db_name = db_name
        self.db_type = db_type
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure the logger with appropriate handlers and level."""
        self.logger.setLevel(logging.DEBUG if self.debug_enabled else logging.INFO)

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG if self.debug_enabled else logging.INFO)

        if _use_json_logging():
            formatter: logging.Formatter = JSONFormatter()
        else:
            formatter = ColoredFormatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def set_debug_enabled(self, debug_enabled: bool) -> None:
        self.debug_enabled = debug_enabled
        self.logger.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
        for handler in self.logger.handlers:
            handler.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

    def set_verbosity(self, verbosity: Verbosity) -> None:
        if not isinstance(verbosity, Verbosity):
            raise TypeError(
                f"verbosity must be a Verbosity member, got {type(verbosity)}"
            )

        self.verbosity = verbosity

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
        """Format database context for log messages with colors."""
        if self.db_name and self.db_type:
            return f"[{colorize(self.db_name, ANSI_COLORS['cyan'])}/{colorize(self.db_type, ANSI_COLORS['magenta'])}]"
        elif self.db_name:
            return f"[{colorize(self.db_name, ANSI_COLORS['cyan'])}]"
        elif self.db_type:
            return f"[{colorize(self.db_type, ANSI_COLORS['magenta'])}]"
        return ""

    def _prefixed(self, msg: str) -> str:
        ctx = self._format_db_context()
        return f"{ctx} {msg}" if ctx else msg

    def _log_best_candidate(self, candidates: Sequence[LogCandidate]) -> None:
        """Log the selected message variant for the current logger state.

        This helper currently assumes there is one log format for each of these
        cases: DEBUG, INFO at VERBOSE verbosity, INFO at NORMAL verbosity, and
        INFO at QUIET verbosity. It only considers DEBUG and INFO candidates
        today. WARNING, ERROR, and CRITICAL candidates could be added here
        later, but they are not part of the current selection logic.

        LogCandidate.log_severity_level is treated as a Python stdlib
        logging level integer here on purpose. Call sites can pass
        logging.DEBUG or logging.INFO directly, which matches what
        logging.Logger expects and keeps severity selection aligned with
        the standard library's level model.
        """
        if self.logger.isEnabledFor(logging.DEBUG):
            for candidate in candidates:
                if candidate.log_severity_level == logging.DEBUG:
                    message = candidate.message_factory()
                    self.debug(self._prefixed(message))
                    return

        if not self.logger.isEnabledFor(logging.INFO):
            return

        info_candidates = [
                candidate
                for candidate in candidates
                if candidate.log_severity_level == logging.INFO
                and self.verbosity >= candidate.log_verbosity_level
        ]

        # No try/except here: each logging helper defines its LogCandidate
        # set statically, so this branch expects well-formed internal
        # candidates rather than arbitrary user-provided input.
        if not info_candidates:
            return

        selected = max(
                info_candidates,
                key=lambda candidate: candidate.log_verbosity_level,
        )

        message = selected.message_factory()
        self.info(self._prefixed(message))

    def log_connection_init(self, db_type: str | None = None) -> None:
        """Log database connection initialization."""
        if db_type:
            self.db_type = db_type
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: "Database connection initialized",
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_pending_migrations(self, migrations: list[str]) -> None:
        """Log list of pending migrations."""
        if migrations:
            self._log_best_candidate(
                [
                    LogCandidate(
                        logging.INFO,
                        lambda: f"Pending migrations ({len(migrations)}):",
                        Verbosity.NORMAL,
                    ),
                ]
            )
            for m in migrations:
                self._log_best_candidate(
                    [
                        LogCandidate(
                            logging.INFO,
                            lambda m=m: (
                                f"  {colorize('[PENDING]', ANSI_COLORS['yellow'])} "
                                f"{colorize(m, ANSI_COLORS['white'])}"
                            ),
                            Verbosity.NORMAL,
                        ),
                    ]
                )

    def log_migration_start(self, version: str, filename: str) -> None:
        """Log migration start."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: f"Starting migration: {filename} (version: {version})",
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_migration_end(self, version: str, filename: str, duration: float) -> None:
        """Log migration end with duration."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[APPLIED]', ANSI_COLORS['green'])} "
                        f"Completed migration: {colorize(filename, ANSI_COLORS['white'])} "
                        f"(version: {colorize(version, ANSI_COLORS['dim'] + ANSI_COLORS['cyan'])}) "
                        f"in {colorize(f'{duration:.2f}s', ANSI_COLORS['dim'])}"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_migration_skipped(self, version: str, filename: str, checksum: str) -> None:
        """Log migration skipped because checksum already applied."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[SKIPPED]', STATUS_COLORS['SKIPPED'])} "
                        f"Migration already applied: {colorize(filename, ANSI_COLORS['white'])} "
                        f"(version: {version}, checksum: {checksum[:16]}...)"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_rollback_start(self, version: str, filename: str) -> None:
        """Log rollback start."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: f"Rolling back migration: {filename} (version: {version})",
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_rollback_end(self, version: str, filename: str, duration: float) -> None:
        """Log rollback end with duration."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[ROLLED_BACK]', ANSI_COLORS['red'])} "
                        f"Rollback completed: {filename} (version: {version}) "
                        f"in {duration:.2f}s"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_sql_statement(self, sql: str) -> None:
        """Log SQL statement with syntax highlighting."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.DEBUG,
                    lambda: "\n".join(
                        [
                            colorize("SQL:", ANSI_COLORS["bold"] + ANSI_COLORS["blue"]),
                            *[
                                colorize_sql(line)
                                for line in sql.strip().split("\n")
                                if line.strip()
                            ],
                        ]
                    ),
                ),
            ]
        )

    def log_backup_created(self, backup_path: str) -> None:
        """Log backup creation."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[APPLIED]', ANSI_COLORS['green'])} "
                        f"Backup created: {backup_path}"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_baseline_set(self, version: str) -> None:
        """Log baseline migration set."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[APPLIED]', ANSI_COLORS['green'])} "
                        f"Baseline set at version: {version}"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_seed_migration(self, filename: str) -> None:
        """Log seed migration."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.INFO,
                    lambda: (
                        f"{colorize('[APPLIED]', ANSI_COLORS['green'])} "
                        f"Seed data applied: {filename}"
                    ),
                    Verbosity.NORMAL,
                ),
            ]
        )

    def log_model_discovered(self, table_name: str, columns: list) -> None:
        """Log model discovered from SQLAlchemy models (debug_enabled only)."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.DEBUG,
                    lambda: f"Discovered model: {table_name} with {len(columns)} columns",
                ),
            ]
        )

    def log_model_paths(self, paths: list[str]) -> None:
        """Log model paths being used (debug_enabled only)."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.DEBUG,
                    lambda: f"Using model paths: {paths}",
                ),
            ]
        )

    def log_table_columns(self, table_name: str, columns: list) -> None:
        """Log table columns (debug_enabled only)."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.DEBUG,
                    lambda: (
                        f"Table {table_name} columns: "
                        f"{', '.join(c['name'] for c in columns)}"
                    ),
                ),
            ]
        )

    def log_migration_sql_gen(self, table_name: str, sql: str) -> None:
        """Log generated migration SQL (debug_enabled only)."""
        self._log_best_candidate(
            [
                LogCandidate(
                    logging.DEBUG,
                    lambda: (
                        f"Generated SQL for {table_name}:\n{colorize_sql(sql)}"
                    ),
                ),
            ]
        )


_global_logger: Optional[DBWardenLogger] = None


def get_logger(
    debug_enabled: bool = False,
    verbose: bool = False,
    verbosity: Verbosity = Verbosity.NORMAL,
    db_name: str | None = None,
    db_type: str | None = None,
) -> DBWardenLogger:
    """
    Get the global DBWarden logger instance.

    Args:
        debug_enabled: If True, sets logger to DEBUG level.
        verbosity: determines the level of density for INFO logs
        db_name: Database name from multi-db config.
        db_type: Database type (sqlite, postgresql, mysql, mariadb, clickhouse).

    Returns:
        DBWardenLogger: The global logger instance.
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = DBWardenLogger(
            debug_enabled=debug_enabled,
            verbosity=verbosity,
            db_name=db_name,
            db_type=db_type,
        )
    else:
        if _global_logger.debug_enabled != debug_enabled:
            _global_logger.set_debug_enabled(debug_enabled)
        if _global_logger.verbosity != verbosity:
            _global_logger.set_verbosity(verbosity)
        if db_name is not None:
            _global_logger.db_name = db_name
        if db_type is not None:
            _global_logger.db_type = db_type
    return _global_logger


def reset_logger() -> None:
    """Reset the global logger instance."""
    global _global_logger
    _global_logger = None
