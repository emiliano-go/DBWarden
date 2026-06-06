from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from dbwarden.commands.migrate import migrate_cmd
from dbwarden.config import get_multi_db_config
from dbwarden.fastapi.runtime import check_startup, compute_pending_migrations
from dbwarden.repositories import check_lock, get_migrated_versions
from dbwarden.repositories.migrations_repo import migrations_table_exists
from dbwarden.repositories.seeds_repo import (
    get_all_seed_records,
    seeds_table_exists,
)


class _MigrateAuthMode(str, Enum):
    OPEN = "open"
    AUTHENTICATED = "authenticated"


class DatabaseStatus(BaseModel):
    database: str
    status: str
    connected: bool
    pending_migrations: int
    applied_migrations: int
    pending_seeds: int
    applied_seeds: int
    lock_active: bool
    error: str | None = None


class StatusResponse(BaseModel):
    databases: dict[str, DatabaseStatus]


class MigrateRequest(BaseModel):
    database: str | None = None
    count: int | None = None
    to_version: str | None = None
    dry_run: bool = False


class MigrateResponse(BaseModel):
    success: bool
    message: str
    database: str | None = None


def _compute_pending_seeds(db_name: str | None) -> int:
    try:
        from dbwarden.engine.seeds import get_pending_seeds

        return len(get_pending_seeds(db_name))
    except Exception:
        return 0


def _compute_applied_seeds(db_name: str | None) -> int:
    try:
        if not seeds_table_exists(db_name):
            return 0
        return len(get_all_seed_records(db_name))
    except Exception:
        return 0


def _compute_applied_migrations(db_name: str | None) -> int:
    try:
        if not migrations_table_exists(db_name):
            return 0
        return len(get_migrated_versions(db_name))
    except Exception:
        return 0


def _compute_migration_status(db_name: str) -> DatabaseStatus:
    pending = compute_pending_migrations(db_name)
    applied = _compute_applied_migrations(db_name)
    pending_seeds = _compute_pending_seeds(db_name)
    applied_seeds = _compute_applied_seeds(db_name)
    lock_active = check_lock(db_name)

    error: str | None = None
    connected = True
    status: str

    try:
        from dbwarden.database.connection import get_db_connection

        with get_db_connection(db_name) as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        connected = True
    except Exception as exc:
        connected = False
        error = str(exc)

    if not connected:
        status = "error"
    elif pending > 0 or pending_seeds > 0:
        status = "degraded"
    else:
        status = "ok"

    return DatabaseStatus(
        database=db_name,
        status=status,
        connected=connected,
        pending_migrations=pending,
        applied_migrations=applied,
        pending_seeds=pending_seeds,
        applied_seeds=applied_seeds,
        lock_active=lock_active,
        error=error,
    )


def DBWardenRouter(
    auth_mode: str = "open",
    api_key: str | None = None,
) -> APIRouter:
    """Create a FastAPI ``APIRouter`` with DBWarden status and migrate endpoints.

    Args:
        auth_mode: ``"open"`` (no auth) or ``"authenticated"`` (API key required).
                   Can also be set via the ``DBWARDEN_MIGRATE_AUTH`` env var.
        api_key: Optional API key for authenticated mode.

    Endpoints:

    * ``GET /status`` — per-database migration and seed status.
    * ``POST /migrate`` — trigger migration execution (auth-guarded when enabled).
    """
    router = APIRouter()
    mode = os.environ.get("DBWARDEN_MIGRATE_AUTH", auth_mode)

    # Shared auth dependency -------------------------------------------------
    header_name = "X-API-Key"
    key_header = APIKeyHeader(name=header_name, auto_error=False)

    async def _require_auth(key: str | None = Depends(key_header)) -> None:
        if mode == "open":
            return
        if not key:
            raise HTTPException(status_code=401, detail="API key required")
        if api_key and key != api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

    # GET /status ------------------------------------------------------------
    @router.get("/status", response_model=StatusResponse)
    async def dbwarden_status(_: None = Depends(_require_auth)) -> JSONResponse:
        cfg = get_multi_db_config()
        results: dict[str, DatabaseStatus] = {}
        for name in cfg.databases:
            results[name] = _compute_migration_status(name)
        return JSONResponse(
            content=StatusResponse(databases=results).model_dump()
        )

    # POST /migrate ----------------------------------------------------------
    @router.post("/migrate", response_model=MigrateResponse)
    async def dbwarden_migrate(
        body: MigrateRequest,
        _: None = Depends(_require_auth),
    ) -> JSONResponse:
        target_db = body.database

        if target_db is not None:
            cfg = get_multi_db_config()
            if target_db not in cfg.databases:
                raise HTTPException(
                    status_code=404,
                    detail=f"Database '{target_db}' not found",
                )

        try:
            migrate_cmd(
                count=body.count,
                to_version=body.to_version,
                database=target_db,
                all_databases=target_db is None,
                dry_run=body.dry_run,
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content=MigrateResponse(
                    success=False,
                    message=str(exc),
                    database=target_db,
                ).model_dump(),
            )

        return JSONResponse(
            content=MigrateResponse(
                success=True,
                message="Migration completed successfully",
                database=target_db,
            ).model_dump()
        )

    return router
