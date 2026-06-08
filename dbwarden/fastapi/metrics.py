from __future__ import annotations

import time

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from dbwarden.fastapi.runtime import resolved_databases
from dbwarden.metrics import (
    generate_metrics,
    metrics_enabled,
    set_pending_migrations,
)


def MetricsRouter() -> APIRouter:
    """Create a FastAPI ``APIRouter`` with a ``GET /metrics`` endpoint.

    The endpoint returns Prometheus text-format metrics.
    It is only active when ``prometheus_client`` is installed **and**
    ``DBWARDEN_METRICS=true`` is set.
    """
    router = APIRouter()

    @router.get("/metrics")
    async def metrics() -> PlainTextResponse:
        if not metrics_enabled():
            return PlainTextResponse(
                "# Metrics disabled (set DBWARDEN_METRICS=true to enable)\n",
                media_type="text/plain; version=0.0.4",
                status_code=200,
            )
        return PlainTextResponse(
            generate_metrics(),
            media_type="text/plain; version=0.0.4",
        )

    return router


class MetricsMiddleware:
    """ASGI middleware that tracks request duration and updates pending-migration gauges.

    This is intentionally lightweight; it refreshes the pending-migration
    gauge once per request so that ``/metrics`` always returns current values.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if metrics_enabled() and scope["type"] == "http":
            start = time.time()
            try:
                await self.app(scope, receive, send)
            finally:
                duration = time.time() - start
                # Refresh pending-migration gauges on each request
                try:
                    for name in resolved_databases(all_databases=True):
                        from dbwarden.fastapi.runtime import compute_pending_migrations

                        count = compute_pending_migrations(name)
                        set_pending_migrations(name, count)
                    from dbwarden.metrics import observe_migration_duration

                    observe_migration_duration("_http_request", scope.get("path", "/"), duration)
                except Exception:
                    pass
        else:
            await self.app(scope, receive, send)
