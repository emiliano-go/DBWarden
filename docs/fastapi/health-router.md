# `DBWardenHealthRouter`

!!! note "Page Moved and Expanded"
    This page has been moved to a comprehensive tutorial with production examples.

## 📍 New Location

**[→ Health Endpoints Tutorial](tutorial/health-endpoints.md)**

The new page includes:
- Response schema documentation
- HTTP status code explanations
- Kubernetes probe examples
- Monitoring integration (Prometheus, Datadog)
- Common use cases
- Troubleshooting guide

---

For quick reference:

## Quick Reference

A mountable FastAPI `APIRouter` that exposes database health and migration state as HTTP endpoints. One import, one `include_router` call, production-ready health checks out of the box.

## Basic usage

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

This registers the following endpoints under the given prefix:

| Method | Path | Description |
|----------|------|-------------|
| `GET` | `/health/` | Overall health — all databases, connectivity + migration state |
| `GET` | `/health/{database_name}` | Health for a single named database |

## Authentication

By default, health endpoints require API key authentication in production. This prevents exposing internal operational details (database names, connection status, pending migrations, error messages) publicly.

### Auth modes

| Mode | Environment | Behavior |
|------|-------------|----------|
| `open` | `DBWARDEN_HEALTH_AUTH=open` | No authentication (suitable for dev/internal networks) |
| `authenticated` | `DBWARDEN_HEALTH_AUTH=authenticated` | Requires `X-API-Key` header (default for production) |

### Configuration

**Via environment variable:**
```bash
# Production - require API key
export DBWARDEN_HEALTH_AUTH=authenticated

# Development - open access
export DBWARDEN_HEALTH_AUTH=open
```

**Via parameter:**
```python
from dbwarden.fastapi import DBWardenHealthRouter

# Open (no auth)
router = DBWardenHealthRouter(auth_mode="open")

# Authenticated with custom key
router = DBWardenHealthRouter(auth_mode="authenticated", api_key="your-secure-key")
```

**Client usage:**
```bash
# Without auth (open mode)
curl http://localhost:8000/health/

# With auth (authenticated mode)
curl -H "X-API-Key: your-secure-key" http://localhost:8000/health/
```

### Security

Error messages are automatically sanitized to remove:
- Credentials in connection strings (`password=...`, `token=...`)
- URL-encoded credentials (`://user:pass@host`)

This prevents leaking sensitive data in health responses.

## Endpoints

### `GET /health/`

Returns health status for all configured databases.

**Response schema:**

```python
class DatabaseHealth(BaseModel):
    database: str                # Database name from config
    status: str                  # "ok" | "degraded" | "error"
    connected: bool              # Whether SELECT 1 succeeded
    pending_migrations: int      # Count of unapplied migrations
    lock_active: bool            # Whether migration lock is held
    error: str | None = None     # Error message if connection failed

class HealthResponse(BaseModel):
    status: str                  # "ok" | "degraded" | "error"
    databases: list[DatabaseHealth]
```

**Overall status rules:**
- `"ok"` → all databases connected and zero pending migrations
- `"degraded"` → all databases connected but one or more has pending migrations
- `"error"` → one or more databases cannot be connected to

**Example response:**

```json
{
  "status": "ok",
  "databases": [
    {
      "database": "primary",
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "lock_active": false,
      "error": null
    },
    {
      "database": "analytics",
      "status": "ok",
      "connected": true,
      "pending_migrations": 0,
      "lock_active": false,
      "error": null
    }
  ]
}
```

### `GET /health/{database_name}`

Returns health status for a single database.

**Response schema:** Same as overall health, but `databases` list contains only one item.

**Example response:**

```json
{
  "status": "degraded",
  "databases": [
    {
      "database": "primary",
      "status": "degraded",
      "connected": true,
      "pending_migrations": 3,
      "lock_active": false,
      "error": null
    }
  ]
}
```

**Error case:**

If the database name is not in config:
- Returns HTTP `404`
- Detail: `"Database 'analytics' not found"`

## HTTP status codes

| Scenario | Status code | Explanation |
|----------|-------------|-------------|
| All databases healthy | `200` | All connected, zero pending migrations |
| Degraded (pending migrations) | `200` | Degraded is a *state*, not a failure — caller decides how to handle |
| Any database unreachable | `503` | Service unavailable — infrastructure should restart or alert |
| Database name not found | `404` | Only for per-database route |

The distinction between `200` and `503` is intentional:
- **Kubernetes liveness probes** care about connectivity (`503` → restart)
- **Kubernetes readiness probes** care about migration state — the caller decides whether pending migrations should block traffic, DBWarden just reports the state

## Health check implementation

For each database, the health check runs:

1. Attempt connection using the cached engine (or build one if not yet cached)
2. Execute a trivial connectivity query (`SELECT 1`)
3. If connectivity fails → mark `connected=False`, `status="error"`, set `error` field, skip migration check
4. If connectivity succeeds → query the configured migration tracking table (default: `_dbwarden_migrations`) to count applied migrations
5. Compare applied count against discovered migration files to compute `pending_migrations`
6. Check if `dbwarden_lock` table has an active lock
7. Return health result

If the migration tracking table does not exist → `pending_migrations` is the total migration file count (nothing has been applied yet).

## Use cases

**Liveness probe (are we alive?):**
```yaml
# kubernetes/deployment.yaml
livenessProbe:
  httpGet:
    path: /health/
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

**Readiness probe (are we ready to serve traffic?):**
```yaml
# kubernetes/deployment.yaml
readinessProbe:
  httpGet:
    path: /health/
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

**Monitoring and alerting:**
```python
import httpx

async def check_app_health():
    response = await httpx.get("http://localhost:8000/health/")
    data = response.json()
    
    if response.status_code == 503:
        alert("Database unreachable!")
    
    if data["status"] == "degraded":
        alert("Pending migrations detected!")
```

**Check specific database before running reports:**
```python
@app.post("/analytics/report")
async def run_report():
    # Check analytics database health before expensive query
    response = await httpx.get("http://localhost:8000/health/analytics")
    data = response.json()
    
    if not data["databases"][0]["connected"]:
        raise HTTPException(503, "Analytics database unavailable")
    
    if data["databases"][0]["pending_migrations"] > 0:
        raise HTTPException(503, "Analytics database has pending migrations")
    
    # Proceed with report generation...
```

## Relationship to `migration_context`

`DBWardenHealthRouter` is the **runtime** health surface. `migration_context` (specifically `check_schema_on_startup`) is the **startup** check.

| | `DBWardenHealthRouter` | `migration_context` startup check |
|---|---|---|
| **When it runs** | On demand (HTTP request) | Once at app boot (in lifespan) |
| **What happens on failure** | Returns HTTP `503`, never blocks | Blocks app boot, prevents startup |
| **Use case** | Runtime monitoring, liveness/readiness probes | Enforce migration state before accepting traffic |

They share the same underlying logic (`check_database_health()` from `dbwarden.fastapi.runtime`) so behavior is consistent between startup and runtime.

## Common patterns

**Production: separate liveness and readiness:**

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()

# Health checks at /health/
app.include_router(DBWardenHealthRouter(), prefix="/health")

# Simple liveness at /ping (doesn't check DB)
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

**Testing: verify all databases are reachable before running integration tests:**

```python
import pytest
from httpx import AsyncClient

@pytest.fixture(scope="session")
async def ensure_databases_healthy():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/")
        assert response.status_code == 200, "Databases not healthy"
        data = response.json()
        assert data["status"] == "ok", f"Databases degraded: {data}"
```

## Navigation

- Previous: [migration_context](migration-context.md)
- Next: [Full Example](full-example.md)
