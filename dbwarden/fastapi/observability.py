from __future__ import annotations

import time
from typing import Any

from dbwarden.metrics import metrics_enabled


class QueryTracingMiddleware:
    """ASGI middleware that emits per-request structured query tracing logs.

    Tracks query count, total duration, slowest query, and slow query
    threshold breaches for each HTTP request.

    Usage::

        from dbwarden.fastapi import QueryTracingMiddleware
        app.add_middleware(QueryTracingMiddleware, slow_query_threshold_ms=100)

    Args:
        app: The ASGI application to wrap.
        slow_query_threshold_ms: Queries exceeding this duration (ms)
          are logged as slow. Default 100.
    """

    def __init__(self, app, slow_query_threshold_ms: int = 100):
        self.app = app
        self.slow_query_threshold_ms = slow_query_threshold_ms

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import logging

        logger = logging.getLogger("dbwarden.tracing")
        start = time.time()
        query_count = 0
        total_query_time = 0.0
        slowest_query_time = 0.0
        slow_queries = 0

        _patch_engine_for_tracing(query_count, total_query_time, slowest_query_time, slow_queries, self.slow_query_threshold_ms)

        try:
            await self.app(scope, receive, send)
        finally:
            duration = time.time() - start
            extras: dict[str, Any] = {
                "path": scope.get("path", "/"),
                "method": scope.get("method", ""),
                "request_duration_ms": round(duration * 1000, 2),
                "query_count": query_count,
                "total_query_time_ms": round(total_query_time * 1000, 2),
                "slowest_query_time_ms": round(slowest_query_time * 1000, 2),
                "slow_queries": slow_queries,
            }
            if slow_queries > 0:
                logger.warning("Slow queries detected", extra=extras)
            else:
                logger.info("Request tracing", extra=extras)

            if metrics_enabled():
                try:
                    from dbwarden.metrics import observe_migration_duration
                    observe_migration_duration("_db_query", scope.get("path", "/"), duration)
                except Exception:
                    pass


class PoolMetricsCollector:
    """Collector for SQLAlchemy connection pool metrics.

    Exposes pool metrics that can be integrated with Prometheus.

    Usage::

        from dbwarden.fastapi import PoolMetricsCollector
        collector = PoolMetricsCollector()

        # In a metrics endpoint or background task:
        metrics = collector.collect()
    """

    def __init__(self):
        self._engines: dict[str, Any] = {}

    def register(self, name: str, engine) -> None:
        """Register an engine for pool metrics collection."""
        self._engines[name] = engine

    def collect(self) -> dict[str, dict[str, int]]:
        """Collect pool metrics from all registered engines.

        Returns::

            {
                "primary": {
                    "pool_size": 5,
                    "checked_out": 2,
                    "overflow": 0,
                    "checked_in": 3,
                }
            }
        """
        metrics: dict[str, dict[str, int]] = {}
        for name, engine in self._engines.items():
            pool = getattr(engine, "pool", None)
            if pool is None:
                continue
            try:
                metrics[name] = {
                    "pool_size": pool.size(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "checked_in": pool.size() - pool.checkedout(),
                }
            except Exception:
                metrics[name] = {"pool_size": 0, "checked_out": 0, "overflow": 0, "checked_in": 0}
        return metrics


def _patch_engine_for_tracing(qc, tqt, sqt, sq, threshold_ms):
    """Monkey-patch SQLAlchemy engine execution to count queries.

    This is a lightweight approach. For production tracing, integrate
    with OpenTelemetry or similar.
    """
    import sqlalchemy as sa

    original_execute = sa.engine.Engine.execute

    def traced_execute(self, statement, *args, **kwargs):
        nonlocal qc, tqt, sqt, sq
        qc += 1
        start = time.time()
        try:
            return original_execute(self, statement, *args, **kwargs)
        finally:
            elapsed = time.time() - start
            tqt += elapsed
            if elapsed > sqt:
                sqt = elapsed
            if elapsed * 1000 > threshold_ms:
                sq += 1

    sa.engine.Engine.execute = traced_execute
