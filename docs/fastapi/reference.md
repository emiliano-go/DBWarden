---
{}
---

# API Reference

Complete API documentation for DBWarden's FastAPI integration.

For most applications, use the `DatabaseHandle` pattern instead of
`get_session()`. Call `database_config()` and use `.async_session`
directly in route parameters: no `Annotated`, `Depends`, or type
aliases needed. See [Session Dependency](tutorial/session-dependency.md).

## `get_session`

Returns a FastAPI dependency that yields an `AsyncSession`.

### Signature

```python
def get_session(
    database: str | None = None,
    *,
    dev: bool = False,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]
```

### Parameters

**`database`** : `str | None`, optional
- Database name from DBWarden config
- If `None`, uses the default database
- Default: `None`

**`dev`** : `bool`, keyword-only, optional
- If `True`, uses `dev_database_url` instead of `database_url`
- Useful for local development
- Default: `False`

### Returns

**`Callable[[], AsyncGenerator[AsyncSession, None]]`**
- A dependency function that FastAPI's `Depends()` can consume
- The dependency yields an `AsyncSession` for each request
- Sessions are automatically closed after the request

### Examples

```python
# Default database
SessionDep = Annotated[AsyncSession, Depends(get_session())]

# Specific database
AnalyticsSessionDep = Annotated[AsyncSession, Depends(get_session("analytics"))]

# Dev mode
DevSessionDep = Annotated[AsyncSession, Depends(get_session(dev=True))]
```

### Raises

- **`ValueError`**: If database type is not supported
- **`DBWardenConfigError`**: If config is not loaded or database not found

---

## `migration_context`

Async context manager for running startup migration checks or migrations.

### Signature

```python
@asynccontextmanager
async def migration_context(
    *,
    mode: Literal["migrate", "check"] = "check",
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    verbose: bool = False,
    allow_in_production: bool = False,
    fail_fast: bool = True,
    only_dev: bool = False,
) -> AsyncGenerator[None, None]
```

### Parameters

**`mode`** : `Literal["migrate", "check"]`, keyword-only, optional
- `"check"` - Read-only validation (recommended for production)
- `"migrate"` - Apply pending migrations
- Default: `"check"`

**`database`** : `str | None`, keyword-only, optional
- Database name to check/migrate
- If `None`, uses default database
- Default: `None`

**`all_databases`** : `bool`, keyword-only, optional
- If `True`, check/migrate all configured databases
- Default: `False`

**`dev`** : `bool`, keyword-only, optional
- Use dev database URL
- Default: `False`

**`strict_translation`** : `bool`, keyword-only, optional
- Enable strict SQL translation mode
- Default: `False`

**`with_backup`** : `bool`, keyword-only, optional
- Create backup before migrations (migrate mode only)
- Default: `False`

**`backup_dir`** : `str | None`, keyword-only, optional
- Directory for backups
- If `None`, uses default location
- Default: `None`

**`verbose`** : `bool`, keyword-only, optional
- Enable detailed logging
- Default: `False`

**`allow_in_production`** : `bool`, keyword-only, optional
- Allow migrate mode in production environment
- Default: `False`

**`fail_fast`** : `bool`, keyword-only, optional
- Exit immediately on failure
- If `False`, logs warning but continues
- Default: `True`

**`only_dev`** : `bool`, keyword-only, optional
- Only run in development environments
- Skipped if `ENVIRONMENT` is production
- Default: `False`

### Returns

**`AsyncGenerator[None, None]`**
- Async context manager for use in FastAPI lifespan

### Examples

```python
# Check mode (recommended)
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", all_databases=True):
        yield

# Migrate mode (dev only)
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(
        mode="migrate",
        only_dev=True,
        with_backup=True,
    ):
        yield
```

### Raises

- **`RuntimeError`**: If checks fail and `fail_fast=True`
- **`ValueError`**: If `mode` is invalid

---

## `check_schema_on_startup`

Run read-only startup schema checks.

### Signature

```python
def check_schema_on_startup(
    *,
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    only_dev: bool = False,
    fail_fast: bool = True,
    verbose: bool = False,
) -> list[HealthResult]
```

### Parameters

Same as `migration_context`, except no migration-specific parameters.

### Returns

**`list[HealthResult]`**
- List of health results, one per database checked
- Each `HealthResult` contains:
  - `database`: str - Database name
  - `status`: str - "ok", "degraded", or "error"
  - `connected`: bool - Whether connection succeeded
  - `pending_migrations`: int - Number of unapplied migrations
  - `lock_active`: bool - Whether migration lock is held
  - `error`: str | None - Error message if failed

### Examples

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    results = check_schema_on_startup(all_databases=True, fail_fast=True)
    for result in results:
        print(f"{result.database}: {result.status}")
    yield
```

### Raises

- **`RuntimeError`**: If any check fails and `fail_fast=True`

---

## `migrate_on_startup`

Run migration workflow at startup.

### Signature

```python
def migrate_on_startup(
    *,
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    verbose: bool = False,
    allow_in_production: bool = False,
    fail_fast: bool = True,
    only_dev: bool = False,
) -> None
```

### Parameters

Same as `migration_context` in migrate mode.

### Returns

**`None`**

### Examples

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate_on_startup(
        all_databases=True,
        with_backup=True,
        only_dev=True,
    )
    yield
```

### Raises

- **`RuntimeError`**: If migration fails and `fail_fast=True`
- **`RuntimeError`**: If in production and `allow_in_production=False`

---

## `DBWardenHealthRouter`

Creates a FastAPI `APIRouter` with health, liveness, and readiness endpoints.

### Signature

```python
def DBWardenHealthRouter(
    auth_mode: str = "open",
    api_key: str | None = None,
) -> APIRouter
```

### Parameters

**`auth_mode`** : `str`, optional
- `"open"` (default) - no authentication required
- `"authenticated"` - requires `X-API-Key` header
- Can also be set via `DBWARDEN_HEALTH_AUTH` env var

**`api_key`** : `str | None`, optional
- API key for authenticated mode

### Returns

**`APIRouter`**
- Router with health endpoints configured
- Routes:
  - `GET /` - Overall health for all databases
  - `GET /liveness` - Always returns 200 (app is alive)
  - `GET /readiness` - Returns 200 when all databases reachable, 503 otherwise
  - `GET /{database_name}` - Health for specific database

### Examples

```python
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()
app.include_router(DBWardenHealthRouter(), prefix="/health")

# Now available:
# GET /health/ - All databases
# GET /health/liveness - Liveness probe
# GET /health/readiness - Readiness probe
# GET /health/primary - Specific database
```

### Response Schema

```python
{
  "status": "ok" | "degraded" | "error",
  "databases": [
    {
      "database": str,
      "status": "ok" | "degraded" | "error",
      "connected": bool,
      "pending_migrations": int,
      "lock_active": bool,
      "error": str | None
    }
  ]
}
```

Liveness response:
```python
{"status": "alive"}
```

### HTTP Status Codes

| Scenario | Status Code |
|----------|-------------|
| All healthy | 200 |
| Degraded (pending migrations) | 200 |
| Database unreachable | 503 |
| Database not found | 404 (per-database route only) |
| App is alive (liveness) | 200 |
| Unauthenticated (auth mode) | 401 |
| Invalid API key (auth mode) | 403 |

---

## `DBWardenRouter`

Creates a FastAPI `APIRouter` with migration status and execution endpoints.

### Signature

```python
def DBWardenRouter(
    auth_mode: str = "open",
    api_key: str | None = None,
) -> APIRouter
```

### Parameters

**`auth_mode`** : `str`, optional
- `"open"` - No authentication required
- `"authenticated"` - Require `X-API-Key` header
- Default: `"open"`

**`api_key`** : `str | None`, optional
- API key for authenticated mode
- If `None`, reads from `DBWARDEN_MIGRATE_AUTH` env var
- Default: `None`

### Returns

**`APIRouter`**
- Router with status and migrate endpoints

### Endpoints

**`GET /status`** - Returns per-database migration and seed status for all configured databases.

**`POST /migrate`** - Triggers migration execution. Accepts JSON body:

```json
{
  "database": "primary",
  "count": null,
  "to_version": null,
  "dry_run": false
}
```

### Examples

```python
from dbwarden.fastapi import DBWardenRouter

app = FastAPI()
app.include_router(DBWardenRouter(), prefix="/db")

# Now available:
# GET /db/status
# POST /db/migrate
```

With authentication:

```python
app.include_router(
    DBWardenRouter(auth_mode="authenticated", api_key="my-secret-key"),
    prefix="/db",
)
```

### Response Schema (GET /status)

```python
{
  "databases": {
    "primary": {
      "database": "primary",
      "status": "ok" | "degraded" | "error",
      "connected": bool,
      "pending_migrations": int,
      "applied_migrations": int,
      "pending_seeds": int,
      "applied_seeds": int,
      "lock_active": bool,
      "error": str | None
    }
  }
}
```

### Response Schema (POST /migrate)

```python
{
  "success": bool,
  "message": str,
  "database": str | None
}
```

### HTTP Status Codes

| Scenario | Status Code |
|----------|-------------|
| Status retrieved successfully | 200 |
| Migrate completed | 200 |
| Migrate dry-run | 200 |
| Auth failure | 403 |
| Migration error | 500 |

---

## `MetricsRouter`

Creates a FastAPI `APIRouter` with a Prometheus metrics endpoint.

### Signature

```python
def MetricsRouter() -> APIRouter
```

### Returns

**`APIRouter`**
- Router with metrics endpoint

### Endpoints

**`GET /metrics`** - Returns Prometheus text-format metrics.

Only active when `prometheus_client` is installed and `DBWARDEN_METRICS=true` is set. Returns 404 when disabled.

### Examples

```python
from dbwarden.fastapi import MetricsRouter

app = FastAPI()
app.include_router(MetricsRouter(), prefix="/metrics")

# Now available:
# GET /metrics
```

### Response format

```
# HELP dbwarden_pending_migrations Number of pending migrations
# TYPE dbwarden_pending_migrations gauge
dbwarden_pending_migrations{database="primary"} 0
# HELP dbwarden_schema_version Current schema version
# TYPE dbwarden_schema_version gauge
dbwarden_schema_version{database="primary"} 5.0
```

---

## `MetricsMiddleware`

ASGI middleware that refreshes pending-migration gauges on each HTTP request.

### Signature

```python
class MetricsMiddleware
```

### Usage

```python
from dbwarden.fastapi import MetricsMiddleware, MetricsRouter

app = FastAPI()
app.add_middleware(MetricsMiddleware)
app.include_router(MetricsRouter(), prefix="/metrics")
```

The middleware also records HTTP request duration via the migration duration histogram.

---

## `dispose_engines`

Close all cached database engines and clients. Should be called during FastAPI shutdown.

### Signature

```python
def dispose_engines() -> None
```

### Examples

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dispose_engines

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    dispose_engines()
```

This closes async and sync session factories, connection pools, and ClickHouse clients for all configured databases.

---

## `dbwarden_lifespan`

Async context manager that handles the full FastAPI engine lifecycle: startup schema validation (or auto-migration), readiness gate, seed application, connection pool warmup, and cleanup on shutdown.

### Signature

```python
async def dbwarden_lifespan(
    app=None,
    *,
    mode: str = "check",           # "check" | "migrate" | "none"
    database: str | None = None,
    all_databases: bool = False,
    dev: bool = False,
    strict_translation: bool = False,
    with_backup: bool = False,
    backup_dir: str | None = None,
    verbose: bool = False,
    allow_in_production: bool = False,
    fail_fast: bool = True,
    only_dev: bool = False,
    readiness_gate: bool = False,
    apply_seeds: bool = False,
    pool_warmup: bool = False,
    pool_warmup_size: int = 3,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app` | `FastAPI` | `None` | FastAPI application instance (optional, for router registration) |
| `mode` | `str` | `"check"` | Startup mode: `"check"` (read-only), `"migrate"` (auto-apply), `"none"` (skip) |
| `database` | `str` | `None` | Target a single database by name |
| `all_databases` | `bool` | `False` | Target all configured databases |
| `readiness_gate` | `bool` | `False` | Raise if any database is unreachable after startup checks |
| `apply_seeds` | `bool` | `False` | Apply pending seed data after migrations |
| `pool_warmup` | `bool` | `False` | Acquire connections before yielding to reduce cold-start latency |
| `pool_warmup_size` | `int` | `3` | Number of connections to acquire during warmup |

The remaining parameters (`dev`, `strict_translation`, `with_backup`, etc.) are identical to
`migration_context()` and control startup check/migration behavior.

### Usage

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dbwarden_lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with dbwarden_lifespan(
        app,
        mode="check",
        readiness_gate=True,
        pool_warmup=True,
        pool_warmup_size=5,
    ):
        yield

app = FastAPI(lifespan=lifespan)
```

---

## `QueryTracingMiddleware`

ASGI middleware that emits per-request structured query tracing logs. Tracks query count, total duration, slowest query, and slow query threshold breaches.

### Signature

```python
def QueryTracingMiddleware(
    app,
    slow_query_threshold_ms: int = 100,
)
```

### Usage

```python
from dbwarden.fastapi import QueryTracingMiddleware

app.add_middleware(QueryTracingMiddleware, slow_query_threshold_ms=100)
```

The middleware monkey-patches SQLAlchemy's `Engine.connect` around each request to count and time queries. On each response, it logs:

| Field | Description |
|-------|-------------|
| `path` | Request path |
| `method` | HTTP method |
| `request_duration_ms` | Total request time |
| `query_count` | Number of database queries |
| `total_query_time_ms` | Cumulative query time |
| `slowest_query_time_ms` | Duration of the slowest query |
| `slow_queries` | Count of queries exceeding the threshold |

Slow queries are logged at `WARNING` level; normal requests at `INFO`.

---

## `PoolMetricsCollector`

Collects SQLAlchemy connection pool metrics for monitoring.

### Signature

```python
class PoolMetricsCollector()
```

### Methods

**`register(name: str, engine)`** - Register an engine for metrics collection.

**`collect() -> dict[str, dict[str, int]]`** - Collect pool metrics from all registered engines.

### Usage

```python
from dbwarden.fastapi import PoolMetricsCollector
from sqlalchemy import create_engine

collector = PoolMetricsCollector()
engine = create_engine("postgresql://localhost/db")
collector.register("primary", engine)

metrics = collector.collect()
# {
#   "primary": {
#     "pool_size": 5,
#     "checked_out": 2,
#     "overflow": 0,
#     "checked_in": 3
#   }
# }
```

---

## `override_database`

Async context manager that temporarily overrides a database URL for testing.

### Signature

```python
async def override_database(
    database: str,
    url: str,
    *,
    run_migrations: bool = False,
    verbose: bool = False,
) -> AsyncGenerator[Any, None]
```

### Parameters

**`database`** : `str` - Database name to override.

**`url`** : `str` - Temporary database URL.

**`run_migrations`** : `bool`, keyword-only, optional - Run pending migrations after override. Default: `False`.

**`verbose`** : `bool`, keyword-only, optional - Enable verbose migration output. Default: `False`.

### Usage

```python
from dbwarden.fastapi import override_database

async with override_database("primary", "sqlite+aiosqlite:///:memory:",
                             run_migrations=True):
    # Test code here uses the overridden database
    ...
# Original URL is restored on exit
```

The original `sqlalchemy_url_sync` and `sqlalchemy_url_async` are restored when the context manager exits, even if an exception occurs.

---

## `migration_state`

Async context manager that simulates a specific migration state for testing by inserting tracking records.

### Signature

```python
async def migration_state(
    applied: list[str] | None = None,
    database: str | None = None,
) -> AsyncGenerator[None, None]
```

### Parameters

**`applied`** : `list[str] | None`, optional - List of version strings to mark as applied. Default: `None`.

**`database`** : `str | None`, optional - Target database name. Default: `None` (uses default database).

### Usage

```python
from dbwarden.fastapi import migration_state

async with migration_state(applied=["0001", "0002"]):
    # Database appears to have migrations 0001 and 0002 applied
    ...
# Tracking records are cleaned up on exit
```

---

## `migration_lock` and `sync_migration_lock`

Redis-backed distributed migration lock context managers for coordinating migrations across multiple application instances.

### Async signature

```python
async def migration_lock(
    redis_client: Any,
    key: str = "dbwarden_migrate",
    ttl: int = 60,
) -> AsyncGenerator[None, None]
```

### Sync signature

```python
def sync_migration_lock(
    redis_client: Any,
    key: str = "dbwarden_migrate",
    ttl: int = 60,
) -> Generator[None, None]
```

### Parameters

**`redis_client`** : `Any`
- Redis client instance (any library with `setnx`, `expire`, `delete` methods)

**`key`** : `str`, optional
- Redis key for the lock
- Default: `"dbwarden_migrate"`

**`ttl`** : `int`, optional
- Lock TTL in seconds (auto-expiry)
- Default: `60`

### Raises

- **`LockError`**: If the lock is already held by another process

### Examples

```python
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from dbwarden.fastapi import migration_context, migration_lock

redis_client = aioredis.from_url("redis://localhost:6379")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_lock(redis_client):
        async with migration_context(mode="migrate"):
            yield
```

```python
import redis
from dbwarden.fastapi import migration_context, sync_migration_lock

redis_client = redis.from_url("redis://localhost:6379")

@asynccontextmanager
async def lifespan(app: FastAPI):
    with sync_migration_lock(redis_client):
        async with migration_context(mode="migrate"):
            yield
```

---

## Type Aliases

### `DatabaseHandle` Pattern (Recommended)

Use `.async_session` and `.sync_session` directly: no type aliases needed:

```python
from dbwarden import database_config

primary = database_config(database_name="primary", ...)


@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

### `SessionDep` (Alternative)

If you prefer the `Annotated` pattern, use `get_session()`:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session())]
```

---

## Data Models

### `HealthResult`

Returned by `check_schema_on_startup`:

```python
@dataclass
class HealthResult:
    database: str           # Database name
    status: str             # "ok", "degraded", or "error"
    connected: bool         # Connection successful?
    pending_migrations: int # Number of unapplied migrations
    lock_active: bool       # Migration lock held?
    error: str | None       # Error message if failed
```

### `DatabaseHealth`

Pydantic model for health endpoints:

```python
class DatabaseHealth(BaseModel):
    database: str
    status: str
    connected: bool
    pending_migrations: int
    lock_active: bool
    error: str | None = None
```

### `HealthResponse`

Pydantic model for health endpoints:

```python
class HealthResponse(BaseModel):
    status: str
    databases: list[DatabaseHealth]
```

---

## Constants

### Environment Detection

DBWarden detects environment from `ENVIRONMENT` variable:

**Development environments:**
- `dev`
- `development`
- `local`
- `test`
- `testing`

**Production environments:**
- `prod`
- `production`

Used by `only_dev` and `allow_in_production` parameters.

---

## Exceptions

### `DBWardenNotInitializedError`

Raised when DBWarden config hasn't been loaded.

```python
# Fix by ensuring dbwarden.py is imported
import dbwarden  # Loads config
```

### `DBWardenDatabaseNotFoundError`

Raised when specified database name doesn't exist in config.

```python
# Fix by adding database to config
db = database_config(
```

---
