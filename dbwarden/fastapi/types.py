from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    database: str
    status: Literal["ok", "degraded", "error"]
    connected: bool
    pending_migrations: int
    lock_active: bool
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    databases: list[DatabaseHealth]
