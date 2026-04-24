from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from dbwarden.commands.migrate import migrate_cmd
from dbwarden.fastapi.runtime import (
    HealthResult,
    check_startup,
    duration_ms,
    is_development_environment,
    is_production_environment,
    runtime_flags,
)
from dbwarden.logging import get_logger


def check_schema_on_startup(
    *,
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    only_dev: bool = False,
    fail_fast: bool = True,
    verbose: bool = False,
) -> list[HealthResult]:
    """Run read-only startup schema checks.

    Returns a list of per-database health results.
    """

    if only_dev and not is_development_environment():
        return []

    logger = get_logger(verbose=verbose)
    with runtime_flags(dev=dev, strict_translation=strict_translation):
        results = check_startup(database=database, all_databases=all_databases)

    bad = [r for r in results if r.status == "error"]
    if bad and fail_fast:
        message = "; ".join(f"{r.database}: {r.error}" for r in bad)
        raise RuntimeError(f"Startup check failed: {message}")
    if bad:
        logger.warning("DBWarden startup check failed but fail_fast=False")
    return results


def migrate_on_startup(
    *,
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    verbose: bool = False,
    allow_in_production: bool = False,
    fail_fast: bool = True,
    only_dev: bool = False,
) -> None:
    """Run migration workflow at startup."""

    if only_dev and not is_development_environment():
        return

    logger = get_logger(verbose=verbose)

    if is_production_environment() and not allow_in_production:
        exc = RuntimeError(
            "migrate_on_startup is blocked in production unless allow_in_production=True"
        )
        if fail_fast:
            raise exc
        logger.warning(str(exc))
        return

    try:
        with runtime_flags(dev=dev, strict_translation=strict_translation):
            migrate_cmd(
                count=None,
                to_version=None,
                verbose=verbose,
                database=database,
                all_databases=all_databases,
                baseline=False,
                with_backup=with_backup,
                backup_dir=backup_dir,
            )
    except Exception:
        if fail_fast:
            raise
        logger.warning("DBWarden migrate_on_startup failed but fail_fast=False")


@asynccontextmanager
async def migration_context(
    *,
    mode: Literal["migrate", "check"] = "check",
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    verbose: bool = False,
    allow_in_production: bool = False,
    fail_fast: bool = True,
    only_dev: bool = False,
):
    """FastAPI lifespan helper for startup migration/check logic."""

    logger = get_logger(verbose=verbose)
    start = __import__("time").time()
    outcome = "ok"

    try:
        if mode == "migrate":
            migrate_on_startup(
                database=database,
                all_databases=all_databases,
                dev=dev,
                strict_translation=strict_translation,
                with_backup=with_backup,
                backup_dir=backup_dir,
                verbose=verbose,
                allow_in_production=allow_in_production,
                fail_fast=fail_fast,
                only_dev=only_dev,
            )
        elif mode == "check":
            check_schema_on_startup(
                database=database,
                all_databases=all_databases,
                dev=dev,
                strict_translation=strict_translation,
                only_dev=only_dev,
                fail_fast=fail_fast,
                verbose=verbose,
            )
        else:
            raise ValueError("mode must be either 'migrate' or 'check'")
    except Exception:
        outcome = "error"
        if fail_fast:
            raise
        logger.warning("DBWarden startup context failed but fail_fast=False")

    logger.info(
        f"migration_context mode={mode} outcome={outcome} duration_ms={duration_ms(start)}"
    )
    yield
