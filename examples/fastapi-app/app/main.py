from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import (
    DBWardenHealthRouter,
    DBWardenRouter,
    dbwarden_lifespan,
)

from app.routes import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(app, mode="check"):
        yield


app = FastAPI(
    title="DBWarden FastAPI Example",
    description="Demonstrates FastAPI integration with DBWarden",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users.router, prefix="/api/v1")
app.include_router(DBWardenHealthRouter(), prefix="/health")
app.include_router(DBWardenRouter(), prefix="/db")


@app.get("/")
async def root():
    return {
        "message": "DBWarden FastAPI Example",
        "docs": "/docs",
        "health": "/health/",
    }
