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
    
    Args:
        auth_mode: "open" (no auth) or "authenticated" (API key required)
                  Can also be set via DBWARDEN_HEALTH_AUTH env var.
        api_key: Optional API key for authenticated mode
    
    For production, set auth_mode="authenticated" or DBWARDEN_HEALTH_AUTH=authenticated
    """
    router = APIRouter()
    mode = os.environ.get("DBWARDEN_HEALTH_AUTH", auth_mode)
    
    if mode == "open":
        @router.get("/", response_model=HealthResponse)
        async def overall_health() -> JSONResponse:
            results = check_startup(all_databases=True)
            payload = [DatabaseHealth(**r.__dict__) for r in results]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

        @router.get("/{database_name}", response_model=HealthResponse)
        async def one_database_health(database_name: str) -> JSONResponse:
            cfg = get_multi_db_config()
            if database_name not in cfg.databases:
                raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found")

            result = check_database_health(database_name)
            payload = [DatabaseHealth(**result.__dict__)]
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
            payload = [DatabaseHealth(**r.__dict__) for r in results]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

        @router.get("/{database_name}", response_model=HealthResponse)
        async def one_database_health(database_name: str, _: None = Depends(require_auth)) -> JSONResponse:
            cfg = get_multi_db_config()
            if database_name not in cfg.databases:
                raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found")

            result = check_database_health(database_name)
            payload = [DatabaseHealth(**result.__dict__)]
            status = _aggregate_status(payload)
            code = _status_to_code(status)
            return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())
    
    return router
