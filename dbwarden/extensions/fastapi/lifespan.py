from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from dbwarden.extensions.fastapi.engines import dispose_engines
from dbwarden.extensions.fastapi.context import migration_context


@asynccontextmanager
async def dbwarden_lifespan(
    app=None,
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
    readiness_gate: bool = False,
    apply_seeds: bool = False,
    pool_warmup: bool = False,
    pool_warmup_size: int = 3,
):
    """FastAPI lifespan context manager for DBWarden.

    Handles the full engine lifecycle: optional startup schema
    validation (or auto-migration), readiness gate, seed application,
    connection pool warmup, and cleanup on shutdown.

    Usage::

        from contextlib import asynccontextmanager
        from fastapi import FastAPI
        from dbwarden.extensions.fastapi import dbwarden_lifespan

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with dbwarden_lifespan(app, mode="check"):
                yield

        app = FastAPI(lifespan=lifespan)

    Parameters
    ----------
    app: FastAPI application instance (optional, for router registration).
    mode:
        - ``"check"``: run read-only schema validation at startup
          (default). Raises on drift unless *fail_fast=False*.
        - ``"migrate"``: auto-apply pending migrations at startup.
          Blocked in production unless *allow_in_production=True*.
        - ``"none"``: skip all startup checks.
    database: Target a single database by name.
    all_databases: Target all configured databases.
    dev: Enable dev-mode SQL translation.
    strict_translation: Raise on untranslatable SQL instead of warning.
    with_backup: Back up before migrating (mode="migrate" only).
    backup_dir: Custom backup directory.
    verbose: Enable verbose logging.
    allow_in_production: Allow auto-migration in production.
    fail_fast: Raise immediately on startup check failure (default True).
    only_dev: Only run checks/migration in development environments.
    readiness_gate: When True, raise if any database is unreachable
      after startup checks.
    apply_seeds: Apply pending seed data after migrations.
    pool_warmup: Acquire pool_warmup_size connections before yielding
      to avoid cold-start latency on first requests.
    pool_warmup_size: Number of connections to acquire during warmup.
    """
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("lifespan"):
        async with HookRegistry.execute_single(
            "lifespan",
            app,
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
            readiness_gate=readiness_gate,
            apply_seeds=apply_seeds,
            pool_warmup=pool_warmup,
            pool_warmup_size=pool_warmup_size,
        ):
            yield
        return

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
                if readiness_gate:
                    _check_readiness(database=database, all_databases=all_databases)
                if apply_seeds:
                    await _apply_seeds(database=database, all_databases=all_databases, verbose=verbose)
                if pool_warmup:
                    _warmup_pools(database=database, all_databases=all_databases, size=pool_warmup_size)
                yield
        else:
            yield
    finally:
        dispose_engines()


def _check_readiness(database: str | None = None, all_databases: bool = False) -> None:
    """Raise RuntimeError if any target database is unreachable."""
    from dbwarden.extensions.fastapi.runtime import check_startup, resolved_databases

    targets = resolved_databases(all_databases) if all_databases else (
        [database] if database else resolved_databases(True)
    )
    for name in targets:
        try:
            from dbwarden.extensions.fastapi.runtime import check_database_health
            result = check_database_health(name)
            if result.status != "ok":
                raise RuntimeError(f"Readiness gate failed: database '{name}' status is '{result.status}'")
        except Exception as exc:
            if not isinstance(exc, RuntimeError):
                raise RuntimeError(f"Readiness gate failed: database '{name}' unreachable: {exc}") from exc
            raise


async def _apply_seeds(database: str | None = None, all_databases: bool = False, verbose: bool = False) -> None:
    """Apply pending seed data."""
    from dbwarden.commands.seeds import seed_apply_cmd

    if all_databases:
        from dbwarden.config import get_multi_db_config
        for db_name in get_multi_db_config().databases:
            seed_apply_cmd(database=db_name, verbose=verbose)
    else:
        seed_apply_cmd(database=database, verbose=verbose)


def _warmup_pools(database: str | None = None, all_databases: bool = False, size: int = 3) -> None:
    """Acquire connections from engine pools to reduce cold-start latency."""
    from dbwarden.config import get_database, get_multi_db_config
    from sqlalchemy import create_engine, text

    targets = list(get_multi_db_config().databases.keys()) if all_databases else (
        [database] if database else [get_multi_db_config().default]
    )
    for name in targets:
        try:
            config = get_database(name)
            url = config.sqlalchemy_url_sync or config.sqlalchemy_url
            if url and not str(url).startswith("clickhouse"):
                engine = create_engine(url)
                connections = []
                for _ in range(min(size, 5)):
                    try:
                        conn = engine.connect()
                        conn.execute(text("SELECT 1"))
                        connections.append(conn)
                    except Exception:
                        break
                for conn in connections:
                    conn.close()
                engine.dispose()
        except Exception:
            pass
