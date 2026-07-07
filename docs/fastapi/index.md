---
description: Integrate DBWarden with FastAPI for automatic schema migration on startup,
  async database sessions, health endpoints, readiness gates, Prometheus metrics,
  and distributed locking.
---

# FastAPI Integration

DBWarden provides first-class FastAPI integration for database sessions, health checks, and migration management.

**One configuration source** for both migrations and runtime: no more split configs.

## Quick Start

Install the FastAPI integration:

```bash
uv add "dbwarden[fastapi]"
```

Create your first FastAPI app with DBWarden:

```python
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(mode="migrate", allow_in_production=True):
        yield

app = FastAPI(lifespan=lifespan)
```

That's it! **5 lines** to integrate DBWarden. For fine-grained control, use `migration_context()` instead of `dbwarden_lifespan()`.

## Tutorial - First Steps

New to DBWarden's FastAPI integration? Start with these tutorials:

1. **[First Steps](tutorial/first-steps.md)** - Get started in 2 minutes
2. **[Session Dependency](tutorial/session-dependency.md)** - Database sessions in routes
3. **[Startup Checks](tutorial/startup-checks.md)** - Validate migrations on boot
4. **[Health Endpoints](tutorial/health-endpoints.md)** - Runtime health monitoring
5. **[Complete Application](tutorial/complete-application.md)** - Full working example

## Advanced User Guide

Ready for more? Learn advanced patterns:

- **[Multi-Database](advanced/multi-database.md)** - Work with multiple databases
- **[Testing](advanced/testing.md)** - Override dependencies and test isolation
- **[Transaction Management](advanced/transaction-management.md)** - Commits, rollbacks, savepoints
- **[Engine Lifecycle](advanced/engine-lifecycle.md)** - Caching, pooling, disposal
- **[Production Patterns](advanced/production-patterns.md)** - Kubernetes, CI/CD, monitoring

## Learn

Understanding the concepts behind DBWarden's FastAPI integration:

- **[Concepts](concepts.md)** - High-level explanations of how it works
- **[API Reference](reference.md)** - Complete function signatures and parameters

## Key Features

### Dependency Injection

Get SQLAlchemy `AsyncSession` in your routes with proper lifecycle management:

```python
from dbwarden import database_config

primary = database_config(database_name="primary", ...)


@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

- No `Annotated`, `Depends`, or type aliases needed
- Automatic engine creation and caching
- Request-scoped sessions
- Automatic cleanup and error handling
- Multi-database support

### Health Endpoints

Production-ready health checks out of the box:

```python
from dbwarden.fastapi import DBWardenHealthRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
```

- Database connectivity checks
- Migration state monitoring
- Kubernetes liveness/readiness probes
- Per-database health status

### Migration Status and Execution

Monitor and trigger migrations at runtime:

```python
from dbwarden.fastapi import DBWardenRouter

app.include_router(DBWardenRouter(), prefix="/db")

# GET /db/status - migration and seed status
# POST /db/migrate - trigger migrations
```

- Per-database migration and seed status
- Runtime migration triggering
- Dry-run support
- Optional API key authentication

### Prometheus Metrics

Expose migration metrics for monitoring:

```python
from dbwarden.fastapi import MetricsRouter, MetricsMiddleware

app.add_middleware(MetricsMiddleware)
app.include_router(MetricsRouter(), prefix="/metrics")
```

- Migration counters and duration histograms
- Schema and seed version gauges
- Pending migration tracking
- Request-scoped gauge refresh

### Distributed Migration Locking

Coordinate migrations across multiple application instances with Redis:

```python
from dbwarden.fastapi import migration_lock, sync_migration_lock
```

- Prevents concurrent migrations across pods
- Async and sync variants available
- Configurable key and TTL

### Engine Lifecycle Management

Properly dispose engines on shutdown:

```python
from dbwarden.fastapi import dispose_engines
```

- Closes all cached engines and clients
- Clean shutdown for async and sync session factories
- ClickHouse client cleanup

### Startup Validation

Ensure your database is ready before accepting traffic:

```python
from contextlib import asynccontextmanager
from dbwarden.fastapi import migration_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", fail_fast=True):
        yield

app = FastAPI(lifespan=lifespan)
```

- Connectivity validation
- Migration state checks
- Optional auto-migration on startup
- Dev/prod environment awareness

## Why Use DBWarden with FastAPI?

**Without DBWarden**, you typically have:
- One config for migrations (Alembic, etc.)
- Another config for your FastAPI app (engines, sessions)
- Manual startup checks
- Custom health endpoints

**With DBWarden**, you have:
- **One configuration source** for everything
- Sessions sourced from your migration config
- Built-in startup validation
- Production-ready health endpoints

**Result:** Less boilerplate, fewer bugs, easier maintenance.

See also: [Cookbook: FastAPI Integration](../cookbook/09-fastapi-integration.md)
