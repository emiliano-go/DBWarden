from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]
DEFAULT_MIGRATION_TABLE = "_dbwarden_migrations"
DEFAULT_SEEDS_TABLE = "_dbwarden_seeds"

_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "site",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "examples",
    "tests",
}


@dataclass
class DatabaseConfig:
    database_type: DatabaseType
    sqlalchemy_url_sync: str | None = None
    sqlalchemy_url_async: str | None = None
    secure_values: bool = False
    secure_display_values: dict[str, str] = field(default_factory=dict)
    model_paths: list[str] | None = None
    model_tables: list[str] | None = None
    migrations_dir: str = "migrations"
    migration_table: str = DEFAULT_MIGRATION_TABLE
    seed_table: str = DEFAULT_SEEDS_TABLE
    auto_apply_seeds: bool = False
    postgres_schema: str | None = None
    dev_database_url: str | None = None
    dev_database_type: DatabaseType | None = None
    overlap_models: bool = False
    pg_extensions: list[str] = field(default_factory=list)
    pg_domains: list[dict] = field(default_factory=list)
    pg_sequences: list[dict] = field(default_factory=list)
    pg_functions: list[dict] = field(default_factory=list)
    pg_triggers: list[dict] = field(default_factory=list)
    pg_roles: list[dict] = field(default_factory=list)
    pg_default_privileges: list[dict] = field(default_factory=list)
    pg_composite_types: list[dict] = field(default_factory=list)
    pg_extended_statistics: list[dict] = field(default_factory=list)
    pg_event_triggers: list[dict] = field(default_factory=list)
    pg_migration_lock_timeout: int | None = None

    @property
    def sqlalchemy_url(self) -> str:
        if self.sqlalchemy_url_sync is not None:
            return self.sqlalchemy_url_sync
        if self.sqlalchemy_url_async:
            return self.sqlalchemy_url_async
        return ""


@dataclass
class MultiDbConfig:
    databases: dict[str, DatabaseConfig] = field(default_factory=dict)
    default: str = "default"


@dataclass
class _ResolvedSource:
    kind: Literal["file", "module"]
    value: str
    classification: Literal["isolated", "in_package"] | None = None
    import_root: str | None = None
    module_name: str | None = None
