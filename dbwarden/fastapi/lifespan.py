from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from dbwarden.fastapi.engines import dispose_engines
from dbwarden.fastapi.context import migration_context


@asynccontextmanager
async def dbwarden_lifespan(
    *,
    mode: Literal["check", "migrate", "none"] = "check",
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
    """FastAPI lifespan context manager for DBWarden.

    Handles the full engine lifecycle: optional startup schema
    validation (or auto-migration), then ordered teardown of all
    engine pools and ClickHouse clients on shutdown.

    Usage in ``app.py``::

        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from dbwarden.fastapi import dbwarden_lifespan

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with dbwarden_lifespan(mode="check"):
                yield

        app = FastAPI(lifespan=lifespan)

    Parameters
    ----------
    mode:
        - ``"check"``: run read-only schema validation at startup
          (default). Raises on drift unless *fail_fast=False*.
        - ``"migrate"``: auto-apply pending migrations at startup.
          Blocked in production unless *allow_in_production=True*.
        - ``"none"``: skip all startup checks; only manage engine
          lifecycle (create on demand, dispose on shutdown).
    database:
        Target a single database by name.
    all_databases:
        Target all configured databases.
    dev:
        Enable dev-mode SQL translation.
    strict_translation:
        Raise on untranslatable SQL instead of warning.
    with_backup:
        Back up the database before migrating (mode="migrate" only).
    backup_dir:
        Custom backup directory.
    verbose:
        Enable verbose logging.
    allow_in_production:
        Allow auto-migration in production (mode="migrate" only).
    fail_fast:
        Raise immediately on startup check failure (default ``True``).
        When ``False``, failures are logged but do not prevent startup.
    only_dev:
        Only run checks/migration in development environments.
    """
    try:
        if mode != "none":
            async with migration_context(
                mode=mode,
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
            ):
                yield
        else:
            yield
    finally:
        dispose_engines()
