from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import text

from dbwarden.config import get_database, get_multi_db_config, is_dev_mode, is_strict_translation, set_dev_mode, set_strict_translation
from dbwarden.database.connection import get_db_connection
from dbwarden.engine.version import get_migration_filepaths_by_version, get_migrations_directory
from dbwarden.repositories import check_lock, get_migrated_versions, migrations_table_exists


@dataclass
class HealthResult:
    database: str
    status: str
    connected: bool
    pending_migrations: int
    lock_active: bool
    error: str | None = None


def is_production_environment() -> bool:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    return env in {"prod", "production"}


def is_development_environment() -> bool:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    return env in {"dev", "development", "local", "test", "testing"}


@contextmanager
def runtime_flags(dev: bool = False, strict_translation: bool = False):
    previous_dev = is_dev_mode()
    previous_strict = is_strict_translation()
    set_dev_mode(dev)
    set_strict_translation(strict_translation)
    try:
        yield
    finally:
        set_dev_mode(previous_dev)
        set_strict_translation(previous_strict)


def resolved_databases(database: str | None = None, all_databases: bool = False) -> list[str]:
    cfg = get_multi_db_config()
    if all_databases:
        return list(cfg.databases.keys())
    return [database or cfg.default]


def compute_pending_migrations(db_name: str | None) -> int:
    migrations_dir = get_migrations_directory(db_name)
    all_files = get_migration_filepaths_by_version(directory=migrations_dir)
    if not migrations_table_exists(db_name):
        return len(all_files)
    applied = set(get_migrated_versions(db_name))
    return len([v for v in all_files if v not in applied])


def check_database_health(db_name: str | None) -> HealthResult:
    label = db_name or get_multi_db_config().default
    try:
        with get_db_connection(db_name) as connection:
            connection.execute(text("SELECT 1"))
        pending = compute_pending_migrations(db_name)
        lock_active = check_lock(db_name)
        return HealthResult(
            database=label,
            status="ok" if pending == 0 else "degraded",
            connected=True,
            pending_migrations=pending,
            lock_active=lock_active,
            error=None,
        )
    except Exception as exc:
        return HealthResult(
            database=label,
            status="error",
            connected=False,
            pending_migrations=0,
            lock_active=False,
            error=str(exc),
        )


def check_startup(database: str | None = None, all_databases: bool = False) -> list[HealthResult]:
    results: list[HealthResult] = []
    for name in resolved_databases(database=database, all_databases=all_databases):
        results.append(check_database_health(name))
    return results


def duration_ms(start_time: float) -> int:
    return int((time.time() - start_time) * 1000)
