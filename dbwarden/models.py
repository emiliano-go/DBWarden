from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MigrationType(Enum):
    """Types of migrations supported by Strata."""

    VERSIONED = "versioned"
    RUNS_ALWAYS = "runs_always"
    RUNS_ON_CHANGE = "runs_on_change"


class MigrationDirection(Enum):
    """Direction of migration operation."""

    UPGRADE = "upgrade"
    ROLLBACK = "rollback"


@dataclass
class MigrationRecord:
    """
    Represents a migration record stored in the database.

    Attributes:
        order_executed: The order in which migrations were executed.
        version: Version identifier for versioned migrations.
        description: Human-readable description of the migration.
        filename: Name of the migration file.
        migration_type: Type of migration (versioned, runs_always, runs_on_change).
        applied_at: Timestamp when the migration was applied.
        checksum: SHA256 checksum of the migration SQL statements.
    """

    order_executed: int
    version: str | None
    description: str
    filename: str
    migration_type: str
    applied_at: datetime
    checksum: str | None


@dataclass
class MigrationFile:
    """
    Represents a migration file on disk.

    Attributes:
        version: Version identifier (None for repeatable migrations).
        filename: Name of the migration file.
        filepath: Full path to the migration file.
        upgrade_sql: SQL statements for upgrading.
        rollback_sql: SQL statements for rollback.
        checksum: Calculated checksum of the upgrade SQL.
    """

    version: str | None
    filename: str
    filepath: str
    upgrade_sql: list[str]
    rollback_sql: list[str]
    checksum: str


@dataclass
class SchemaDifference:
    """
    Represents a difference between models and database schema.

    Attributes:
        type: Type of difference (add_table, drop_table, add_column, etc.)
        table_name: Name of the affected table.
        column_name: Name of the affected column (if applicable).
        sql: The SQL statement to resolve the difference.
    """

    type: str
    table_name: str
    column_name: str | None = None
    sql: str = ""


@dataclass
class SeedRecord:
    version: str
    description: str
    filename: str
    seed_type: str
    applied_at: datetime
    checksum: str | None = None


@dataclass
class SafetyIssue:
    severity: str
    change_type: str
    table_name: str
    message: str
    column_name: str | None = None
    sql: str = ""
    required_flag: str | None = None
