from __future__ import annotations

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    database: str
    status: str
    connected: bool
    pending_migrations: int
    lock_active: bool
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    databases: list[DatabaseHealth]
