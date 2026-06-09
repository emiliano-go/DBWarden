from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import (
    DBWardenHealthRouter,
    dbwarden_lifespan,
    MetricsMiddleware,
    MetricsRouter,
    PoolMetricsCollector,
    QueryTracingMiddleware,
)

from app.models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check"):
        yield


app = FastAPI(
    title="DBWarden Observability Example",
    lifespan=lifespan,
)

# Observability middleware (order matters — MetricsMiddleware first)
app.add_middleware(QueryTracingMiddleware)
app.add_middleware(MetricsMiddleware)

# Metrics endpoint
app.include_router(MetricsRouter(), prefix="/metrics")

# Health endpoint
app.include_router(DBWardenHealthRouter(), prefix="/health")


@app.get("/")
async def root():
    return {"message": "DBWarden Observability Example"}
