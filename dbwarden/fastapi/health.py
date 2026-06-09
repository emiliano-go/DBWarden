from __future__ import annotations

import os
from enum import Enum
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from dbwarden.config import get_multi_db_config
from dbwarden.fastapi.runtime import check_database_health, check_startup
from dbwarden.fastapi.types import DatabaseHealth, HealthResponse


class HealthAuthMode(str, Enum):
    OPEN = "open"
    AUTHENTICATED = "authenticated"


def _aggregate_status(items: list[DatabaseHealth]) -> str:
    if any(i.status == "error" for i in items):
        return "error"
    if any(i.status == "degraded" for i in items):
        return "degraded"
    return "ok"


def _status_to_code(status: str) -> int:
    if status == "ok":
        return 200
    if status == "degraded":
        return 200
    return 503


def DBWardenHealthRouter(
    auth_mode: str = "open",
    api_key: str | None = None,
) -> APIRouter:
    """Create DBWarden FastAPI health router.

    Endpoints:

    - ``GET /`` — overall health across all databases (200/503).
    - ``GET /{database_name}`` — health for a single database.
    - ``GET /liveness`` — always returns 200 (app is alive).
    - ``GET /readiness`` — returns 200 when all databases are
      reachable, 503 otherwise.

    Args:
        auth_mode: "open" (no auth) or "authenticated" (API key required).
          Can also be set via ``DBWARDEN_HEALTH_AUTH`` env var.
        api_key: Optional API key for authenticated mode.

    For production, set ``auth_mode="authenticated"`` or
    ``DBWARDEN_HEALTH_AUTH=authenticated``.
    """
    from pydantic import BaseModel

    class LivenessResponse(BaseModel):
        status: str = "alive"

    class ReadinessResponse(BaseModel):
        status: str
        databases: list[DatabaseHealth]

    router = APIRouter()
    mode = os.environ.get("DBWARDEN_HEALTH_AUTH", auth_mode)
    
    if mode == "open":
        @router.get("/", response_model=HealthResponse)
        async def overall_health() -> JSONResponse:
            results = check_startup(all_databases=True)
            payload = [r.to_database_health() for r in results]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

        @router.get("/liveness")
        async def liveness() -> LivenessResponse:
            return LivenessResponse(status="alive")

        @router.get("/readiness")
        async def readiness() -> ReadinessResponse:
            results = check_startup(all_databases=True)
            payload = [r.to_database_health() for r in results]
            status = _aggregate_status(payload)
            code = 200 if status == "ok" else 503
            return JSONResponse(status_code=code, content=ReadinessResponse(status=status, databases=payload).model_dump())

        @router.get("/{database_name}", response_model=HealthResponse)
        async def one_database_health(database_name: str) -> JSONResponse:
            cfg = get_multi_db_config()
            if database_name not in cfg.databases:
                raise HTTPException(status_code=404, detail="Database not found")

            result = check_database_health(database_name)
            payload = [result.to_database_health()]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())
    else:
        header_name = "X-API-Key"
        key_header = APIKeyHeader(name=header_name, auto_error=False)
        
        async def require_auth(key: str = Depends(key_header)) -> None:
            if not key:
                raise HTTPException(status_code=401, detail="API key required")
            if api_key and key != api_key:
                raise HTTPException(status_code=403, detail="Invalid API key")

        @router.get("/", response_model=HealthResponse)
        async def overall_health(_: None = Depends(require_auth)) -> JSONResponse:
            results = check_startup(all_databases=True)
            payload = [r.to_database_health() for r in results]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

        @router.get("/liveness")
        async def liveness(_: None = Depends(require_auth)) -> LivenessResponse:
            return LivenessResponse(status="alive")

        @router.get("/readiness")
        async def readiness(_: None = Depends(require_auth)) -> ReadinessResponse:
            results = check_startup(all_databases=True)
            payload = [r.to_database_health() for r in results]
            status = _aggregate_status(payload)
            code = 200 if status == "ok" else 503
            return JSONResponse(status_code=code, content=ReadinessResponse(status=status, databases=payload).model_dump())

        @router.get("/{database_name}", response_model=HealthResponse)
        async def one_database_health(database_name: str, _: None = Depends(require_auth)) -> JSONResponse:
            cfg = get_multi_db_config()
            if database_name not in cfg.databases:
                raise HTTPException(status_code=404, detail="Database not found")

            result = check_database_health(database_name)
            payload = [result.to_database_health()]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())
    
    return router
