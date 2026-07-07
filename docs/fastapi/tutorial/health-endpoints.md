---
{}
---

# Health Endpoints

Learn how to add database health monitoring to your FastAPI application.

## What Are Health Endpoints?

Health endpoints are HTTP endpoints that report whether your application and its dependencies (like databases) are working correctly.

They're essential for:
- **Kubernetes liveness probes** - Is the app alive?
- **Kubernetes readiness probes** - Is the app ready to serve traffic?
- **Monitoring systems** - Prometheus, Datadog, New Relic, etc.
- **Load balancers** - Should traffic be routed here?
- **Debugging** - Quick status check during incidents

## Quick Example

Add health endpoints to your app in **one line**:

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

That's it! You now have:
- `GET /health/` - Overall health for all databases
- `GET /health/{database_name}` - Health for a specific database

## Your First Health Check

Let's start with a complete minimal example:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)

# Add health endpoints
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Start your app:

```bash
uvicorn main:app --reload
```

## Test Your Endpoints

### Check Overall Health

```bash
curl http://localhost:8000/health/
```

Response:

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
    }
  ]
}
```

### Check Specific Database

```bash
curl http://localhost:8000/health/primary
```

Response:

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
    }
  ]
}
```

For prettier output, use [httpie](https://httpie.io/):
```bash
http :8000/health/
```

## Understanding the Response

Let's break down what each field means:

### Response Schema

```python
{
  "status": str,           # Overall status: "ok" | "degraded" | "error"
  "databases": [           # List of database health details
    {
      "database": str,     # Database name from config
      "status": str,       # This database's status: "ok" | "degraded" | "error"
      "connected": bool,   # Can we execute SELECT 1?
      "pending_migrations": int,  # Number of unapplied migrations
      "lock_active": bool, # Is a migration currently running?
      "error": str | None  # Error message if connection failed
    }
  ]
}
```

### Status Values

**`"ok"`** - Everything is healthy
-  Database is connected
-  Zero pending migrations
-  No migration lock

**`"degraded"`** - Functional but needs attention
-  Database is connected
-  Has pending migrations
- ℹ App works but schema is outdated

**`"error"`** - Not functional
-  Cannot connect to database
-  Health check failed

### Overall Status Logic

The overall `status` field follows these rules:

```python
if any database has status "error":
    overall_status = "error"
elif any database has status "degraded":
    overall_status = "degraded"
else:
    overall_status = "ok"
```

## HTTP Status Codes

DBWarden health endpoints return these HTTP status codes:

| Scenario | HTTP Status | Overall Status |
|----------|-------------|----------------|
| All databases healthy | **200** | `"ok"` |
| Pending migrations exist | **200** | `"degraded"` |
| Database unreachable | **503** | `"error"` |
| Database name not found | **404** | N/A |

Pending migrations are a state, not a failure. The app still works, the schema is just outdated. You decide whether to block traffic on degraded state.

### Why These Status Codes Matter

**200 OK** - App is functional
- Continue routing traffic
- Report as healthy to load balancers
- Use for readiness probes (optionally)

**503 Service Unavailable** - App cannot function
- Stop routing traffic
- Restart the pod (liveness probe)
- Alert the on-call engineer

**404 Not Found** - Configuration error
- Database name doesn't exist in config
- Only returned for per-database route

## Health Check Flow

Here's what happens when you hit `/health/`:

```
1. Request arrives  /health/
2. For each database in config:
   a. Get or create engine
   b. Attempt connection
   c. Execute SELECT 1
   d. If connected:
      - Count applied migrations
      - Count total migration files
      - Calculate pending = total - applied
      - Check migration lock status
   e. If connection fails:
      - Set status = "error"
      - Set error message
      - Skip migration checks
3. Aggregate all database statuses
4. Return JSON response with appropriate HTTP status
```

### What Gets Checked

For **each database**, DBWarden checks:

1. **Connectivity** - Can we connect? (`SELECT 1`)
2. **Migration state** - Are migrations pending?
3. **Migration lock** - Is a migration currently running?

Health checks are fast - they only run `SELECT 1` and query the configured migration tracking table (default: `_dbwarden_migrations`). No expensive queries or full schema scans.

## Common Use Cases

### Kubernetes Liveness Probe

Liveness probes check if your app is alive. If it fails, Kubernetes restarts the pod.

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
          failureThreshold: 3
```

This checks health every 30 seconds. If it fails 3 times in a row, Kubernetes restarts the pod.

### Kubernetes Readiness Probe

Readiness probes check if your app is ready to serve traffic. If it fails, Kubernetes stops routing to the pod (but doesn't restart it).

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  template:
    spec:
      containers:
      - name: app
        image: myapp:latest
        readinessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

This checks health every 10 seconds. If degraded or error, traffic stops routing to this pod.

If you use `/health/` for readiness and have pending migrations, your pods will be marked not ready and receive no traffic. This might be what you want, or you might want a separate `/ping` endpoint for basic liveness.

### Separate Liveness and Readiness

For more control, use different endpoints:

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()

# Database health at /health/ (for readiness)
app.include_router(DBWardenHealthRouter(), prefix="/health")

# Simple ping at /ping (for liveness)
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

Then configure Kubernetes:

```yaml
livenessProbe:
  httpGet:
    path: /ping      # Simple check - app is alive
    port: 8000
readinessProbe:
  httpGet:
    path: /health/   # Full check - app is ready
    port: 8000
```

### Monitoring and Alerting

Use health endpoints to feed monitoring systems:

#### Prometheus

Create a script that exports metrics:

```python
# monitoring/exporter.py
import httpx
from prometheus_client import Gauge, start_http_server

database_health = Gauge('dbwarden_database_health', 'Database health status', ['database'])
pending_migrations = Gauge('dbwarden_pending_migrations', 'Pending migrations', ['database'])

async def collect_metrics():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health/")
        data = response.json()
        
        for db in data["databases"]:
            # 1 = ok, 0.5 = degraded, 0 = error
            health_value = 1 if db["status"] == "ok" else (0.5 if db["status"] == "degraded" else 0)
            database_health.labels(database=db["database"]).set(health_value)
            pending_migrations.labels(database=db["database"]).set(db["pending_migrations"])

if __name__ == "__main__":
    start_http_server(9090)
    # Run collect_metrics periodically
```

#### Datadog

```python
# monitoring/datadog.py
import httpx
from datadog import statsd

async def report_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health/")
        data = response.json()
        
        for db in data["databases"]:
            statsd.gauge(
                'app.database.pending_migrations',
                db["pending_migrations"],
                tags=[f'database:{db["database"]}']
            )
            
            statsd.service_check(
                'app.database.health',
                statsd.OK if db["status"] == "ok" else statsd.WARNING,
                tags=[f'database:{db["database"]}']
            )
```

### Pre-Query Health Check

Check database health before running expensive operations:

```python
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

@app.post("/analytics/generate-report")
async def generate_report():
    # Check if analytics database is healthy
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health/analytics")
        data = response.json()
        
        db_health = data["databases"][0]
        
        if not db_health["connected"]:
            raise HTTPException(
                status_code=503,
                detail="Analytics database unavailable"
            )
        
        if db_health["pending_migrations"] > 0:
            raise HTTPException(
                status_code=503,
                detail=f"Analytics database has {db_health['pending_migrations']} pending migrations"
            )
    
    # Proceed with expensive report generation
    ...
```

### Load Balancer Health Checks

Configure your load balancer (ALB, nginx, etc.) to check `/health/`:

#### AWS Application Load Balancer

```yaml
# target-group.yaml
TargetGroup:
  HealthCheckPath: /health/
  HealthCheckIntervalSeconds: 30
  HealthCheckTimeoutSeconds: 5
  HealthyThresholdCount: 2
  UnhealthyThresholdCount: 3
  Matcher:
    HttpCode: 200
```

#### Nginx

```nginx
# nginx.conf
upstream myapp {
    server app1:8000;
    server app2:8000;
    server app3:8000;
    
    # Health check
    check interval=10000 rise=2 fall=3 timeout=5000 type=http;
    check_http_send "GET /health/ HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

## Relationship to Startup Checks

Health endpoints and startup checks serve different purposes:

| | **Health Endpoints** | **Startup Checks** |
|---|---|---|
| **When** | On demand (HTTP request) | Once at app boot |
| **Failure** | Returns HTTP 503 | Blocks app startup |
| **Use case** | Runtime monitoring | Enforce readiness before traffic |
| **Frequency** | Every request | Once |

### Startup Check (Lifespan)

```python
from contextlib import asynccontextmanager
from dbwarden.fastapi import migration_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", fail_fast=True):
        #  If this fails, app won't start
        yield
```

### Runtime Health (HTTP Endpoint)

```python
from dbwarden.fastapi import DBWardenHealthRouter

#  Always available - returns status code based on health
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Both use the same underlying `check_database_health()` function, so behavior is consistent.

## Common Patterns

### Pattern 1: Basic Health Only

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

### Pattern 2: Health + Simple Ping

```python
from fastapi import FastAPI
from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()

# Database health (readiness)
app.include_router(DBWardenHealthRouter(), prefix="/health")

# Simple ping (liveness)
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

### Pattern 3: Custom Prefix

```python
# Health at /api/v1/health/
app.include_router(DBWardenHealthRouter(), prefix="/api/v1/health")
```

### Pattern 4: With Tags for Documentation

```python
# Show in OpenAPI docs with "Health" tag
router = DBWardenHealthRouter()
router.tags = ["Health"]
app.include_router(router, prefix="/health")
```

## Troubleshooting

### 503 Errors in Production

If you're getting 503 errors, check:

1. **Is the database reachable?**
   ```bash
   # Check database connectivity
   curl http://localhost:8000/health/ | jq '.databases[].error'
   ```

2. **Are migrations pending?**
   ```bash
   # Check pending migrations
   curl http://localhost:8000/health/ | jq '.databases[].pending_migrations'
   ```

3. **Is a migration lock active?**
   ```bash
   # Check lock status
   curl http://localhost:8000/health/ | jq '.databases[].lock_active'
   ```

### Degraded State in Production

If your app is marked degraded:

```json
{
  "status": "degraded",
  "databases": [
    {
      "pending_migrations": 3,
      ...
    }
  ]
}
```

This means migrations need to be applied:

```bash
# Apply migrations
$ dbwarden migrate

# Or let the app auto-migrate (if configured)
# See: Startup Checks documentation
```

### 404 on Per-Database Route

```bash
curl http://localhost:8000/health/analytics
# 404: Database 'analytics' not found
```

Check your DBWarden config - the database name must be defined:

```python
# dbwarden.py
analytics = database_config(
    database_name="analytics",  #  Must match route parameter
    ...
)
```

### Health Check Too Slow

Health checks should be fast (< 100ms). If they're slow:

1. **Database connection is slow** - Check network latency
2. **Migration table is huge** - Consider squashing migrations
3. **Multiple databases** - Each one adds latency

For very fast health checks, consider:

```python
# Simple ping (no database check)
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

## What's Next?

- **[Startup Checks](startup-checks.md)** - Validate on app boot
- **[Complete Application](complete-application.md)** - Full working example
- **[Production Patterns](../advanced/production-patterns.md)** - K8s, CI/CD, monitoring
- **[Multi-Database](../advanced/multi-database.md)** - Multiple databases
