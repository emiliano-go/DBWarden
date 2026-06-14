from __future__ import annotations

import os
import re
from typing import Any

_VERSION_RE = re.compile(r"(\d+)")


def _parse_version(version: str) -> float:
    match = _VERSION_RE.search(version)
    if match:
        return float(match.group(1))
    return 0.0


def _noop(*args: Any, **kwargs: Any) -> None:
    pass


try:
    import prometheus_client

    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


if _HAS_PROMETHEUS:
    _REGISTRY = prometheus_client.CollectorRegistry()

    _migrations_total = prometheus_client.Counter(
        "dbwarden_migrations_total",
        "Total number of migrations applied",
        labelnames=["database", "version", "success"],
    )

    _migration_duration = prometheus_client.Histogram(
        "dbwarden_migration_duration_seconds",
        "Duration of individual migration steps in seconds",
        labelnames=["database", "version"],
        buckets=(
            0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")
        ),
    )

    _schema_version = prometheus_client.Gauge(
        "dbwarden_schema_version",
        "Applied schema version per database",
        labelnames=["database"],
    )

    _seed_version = prometheus_client.Gauge(
        "dbwarden_seed_version",
        "Applied seed version per database",
        labelnames=["database"],
    )

    _pending_migrations = prometheus_client.Gauge(
        "dbwarden_migrations_pending",
        "Number of pending migrations per database",
        labelnames=["database"],
    )

    _migration_errors = prometheus_client.Counter(
        "dbwarden_migration_errors_total",
        "Total number of migration failures",
        labelnames=["database"],
    )

    def increment_migrations_total(
        database: str, version: str, success: bool = True
    ) -> None:
        _migrations_total.labels(
            database=database, version=version, success=str(success)
        ).inc()

    def observe_migration_duration(
        database: str, version: str, duration: float
    ) -> None:
        _migration_duration.labels(database=database, version=version).observe(duration)

    def set_schema_version(database: str, version: str) -> None:
        _schema_version.labels(database=database).set(_parse_version(version))

    def set_seed_version(database: str, version: str) -> None:
        _seed_version.labels(database=database).set(_parse_version(version))

    def set_pending_migrations(database: str, count: int) -> None:
        _pending_migrations.labels(database=database).set(count)

    def increment_migration_errors(database: str) -> None:
        _migration_errors.labels(database=database).inc()

    def generate_metrics() -> str:
        return prometheus_client.generate_latest().decode("utf-8")

    def metrics_enabled() -> bool:
        return os.environ.get("DBWARDEN_METRICS", "false").lower() in (
            "true",
            "1",
            "yes",
        )

else:
    increment_migrations_total = _noop
    observe_migration_duration = _noop
    set_schema_version = _noop
    set_seed_version = _noop
    set_pending_migrations = _noop
    increment_migration_errors = _noop

    def generate_metrics() -> str:
        return ""

    def metrics_enabled() -> bool:
        return os.environ.get("DBWARDEN_METRICS", "false").lower() in (
            "true",
            "1",
            "yes",
        )
