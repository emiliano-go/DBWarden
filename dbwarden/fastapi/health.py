from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from dbwarden.config import get_multi_db_config
from dbwarden.fastapi.runtime import check_database_health, check_startup
from dbwarden.fastapi.types import DatabaseHealth, HealthResponse


def _aggregate_status(items: list[DatabaseHealth]) -> str:
    if any(i.status == "error" for i in items):
        return "error"
    if any(i.status == "degraded" for i in items):
        return "degraded"
    return "ok"


def DBWardenHealthRouter() -> APIRouter:
    """Create DBWarden FastAPI health router.

    Routes:
      GET /      -> overall health
      GET /{database_name} -> per-database health
    """

    router = APIRouter()

    @router.get("/", response_model=HealthResponse)
    async def overall_health() -> JSONResponse:
        results = check_startup(all_databases=True)
        payload = [DatabaseHealth(**r.__dict__) for r in results]
        status = _aggregate_status(payload)
        code = 200 if status == "ok" else 503
        return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

    @router.get("/{database_name}", response_model=HealthResponse)
    async def one_database_health(database_name: str) -> JSONResponse:
        cfg = get_multi_db_config()
        if database_name not in cfg.databases:
            raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found")

        result = check_database_health(database_name)
        payload = [DatabaseHealth(**result.__dict__)]
        status = _aggregate_status(payload)
        code = 200 if status == "ok" else 503
        return JSONResponse(status_code=code, content=HealthResponse(status=status, databases=payload).model_dump())

    return router
