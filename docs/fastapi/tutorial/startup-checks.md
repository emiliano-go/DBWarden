---
{}
---

# Startup Checks

Learn how to validate your database before your FastAPI app accepts traffic.

## What Are Startup Checks?

Startup checks run when your app boots, **before** it starts accepting requests. They verify:

-  Database connectivity
-  Migration state
-  Schema integrity

If checks fail, your app won't start. This prevents serving traffic with a broken or outdated database.

## Why Use Startup Checks?

**Without startup checks:**
- App starts even if database is down
- First requests fail with connection errors
- Users see errors while you debug
- Hard to diagnose deployment issues

**With startup checks:**
- App fails to start if database has issues
- Kubernetes restarts the pod automatically
- No user-facing errors
- Clear logs showing what's wrong

## Quick Example

Add a startup check in **3 lines**:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield  # App runs here


app = FastAPI(lifespan=lifespan)
```

That's it! Your app now validates the database on startup.

## Your First Startup Check

Let's start with a complete minimal example:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs before app starts accepting requests
    async with migration_context(mode="check"):
        yield  # App serves traffic
    # Runs on shutdown (cleanup)


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World"}
```

Start your app:

```bash
uvicorn main:app
```

### If Database Is Healthy

You'll see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     DBWarden: migration_context mode=check outcome=ok duration_ms=45
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The app starts successfully!

### If Database Has Issues

If the database is unreachable or has pending migrations:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
ERROR:    Application startup failed. Exiting.
RuntimeError: Startup check failed: primary: could not connect to server
```

The app **exits immediately**. No requests are served.

Failing fast on startup is better than serving broken requests. Kubernetes will restart your pod automatically.

## Check Mode vs Migrate Mode

`migration_context` has two modes:

### Check Mode (Recommended)

Validates without making changes:

```python
async with migration_context(mode="check"):
    yield
```

**What it does:**
-  Checks database connectivity
-  Verifies migration state
-  Reports pending migrations
-  Does **not** apply migrations
-  Does **not** modify schema

**Use for:**
- Production deployments
- Staging environments
- When migrations run in separate jobs

### Migrate Mode

Applies migrations on startup:

```python
async with migration_context(mode="migrate"):
    yield
```

**What it does:**
-  Checks database connectivity
-  Applies pending migrations
-  Updates schema
-  Modifies your database

**Use for:**
- Local development
- Simple deployments
- Single-instance apps
- When you want auto-migration

Migrate mode is blocked in production by default. Set `allow_in_production=True` to override (not recommended for most apps).

## Complete Function Signature

```python
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
) -> AsyncContextManager:
    """FastAPI lifespan helper for startup migration/check logic."""
```

## All Parameters

### `mode`

**Type:** `"check"` | `"migrate"`  
**Default:** `"check"`

What to do on startup:
- `"check"` - Read-only validation (recommended)
- `"migrate"` - Apply pending migrations

```python
# Check only (recommended for production)
async with migration_context(mode="check"):
    yield

# Apply migrations (useful for dev)
async with migration_context(mode="migrate"):
    yield
```

### `database`

**Type:** `str | None`  
**Default:** `None` (uses default database)

Which database to check/migrate:

```python
# Check default database
async with migration_context(mode="check"):
    yield

# Check specific database
async with migration_context(mode="check", database="analytics"):
    yield
```

### `all_databases`

**Type:** `bool`  
**Default:** `False`

Check/migrate all configured databases:

```python
# Check all databases
async with migration_context(mode="check", all_databases=True):
    yield
```

If you have multiple databases and want to validate all of them on startup, use this.

For apps with multiple databases, always use `all_databases=True` in production to ensure all databases are healthy.

### `dev`

**Type:** `bool`  
**Default:** `False`

Use `dev_database_url` instead of `database_url`:

```python
# Use dev database
async with migration_context(mode="check", dev=True):
    yield
```

Or set environment variable:

```bash
export ENVIRONMENT=development
```

### `strict_translation`

**Type:** `bool`  
**Default:** `False`

Enable strict SQL translation mode (advanced):

```python
async with migration_context(mode="check", strict_translation=True):
    yield
```

### `with_backup`

**Type:** `bool`  
**Default:** `False`

Create backup before migrations (migrate mode only):

```python
async with migration_context(
    mode="migrate",
    with_backup=True,
    backup_dir="./backups"
):
    yield
```

This parameter only applies when `mode="migrate"`. Ignored in check mode.

### `backup_dir`

**Type:** `str | None`  
**Default:** `None` (uses default backup location)

Where to store backups:

```python
async with migration_context(
    mode="migrate",
    with_backup=True,
    backup_dir="/var/backups/dbwarden"
):
    yield
```

### `verbose`

**Type:** `bool`  
**Default:** `False`

Enable detailed logging:

```python
async with migration_context(mode="check", verbose=True):
    yield
```

Useful for debugging startup issues.

### `allow_in_production`

**Type:** `bool`  
**Default:** `False`

Allow migrate mode in production:

```python
async with migration_context(
    mode="migrate",
    allow_in_production=True  #  Use with caution
):
    yield
```

By default, `mode="migrate"` is **blocked** when `ENVIRONMENT` is `prod` or `production`. This prevents accidental schema changes in production.

Only enable this if you understand the risks: no rollback on migration failure, downtime during migration, potential data loss, and race conditions with multiple pods.

**Better approach:** Run migrations in a separate job before deployment.

### `fail_fast`

**Type:** `bool`  
**Default:** `True`

Exit immediately on failure:

```python
# Fail fast (recommended)
async with migration_context(mode="check", fail_fast=True):
    yield

# Continue on failure (not recommended)
async with migration_context(mode="check", fail_fast=False):
    yield
```

When `fail_fast=True`:
- App exits if checks fail
- Clear error message in logs
- Kubernetes restarts pod

When `fail_fast=False`:
- Logs warning but continues
- App starts even with database issues
- First requests may fail

`fail_fast=True` is the right default for production. If you can't start, you shouldn't serve traffic.

### `only_dev`

**Type:** `bool`  
**Default:** `False`

Only run checks in development environments:

```python
# Only check in dev, skip in prod
async with migration_context(mode="check", only_dev=True):
    yield
```

This skips checks unless `ENVIRONMENT` is one of:
- `dev`
- `development`
- `local`
- `test`
- `testing`

**When to use:**
- You run migrations in CI/CD before deployment
- You have separate health checks in production
- You want faster production startup

If you use `only_dev=True`, make sure you have other mechanisms to validate database health in production (like health endpoints or separate migration jobs).

## Common Patterns

### Pattern 1: Production - Check Only

Recommended for most production apps:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(
        mode="check",
        all_databases=True,
        fail_fast=True,
    ):
        yield

app = FastAPI(lifespan=lifespan)
```

-  Validates all databases
-  Fails fast on issues
-  No schema changes
-  Safe for multiple pods

### Pattern 2: Development - Auto Migrate

Convenient for local development:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(
        mode="migrate",
        only_dev=True,  # Only in dev
        with_backup=True,
        verbose=True,
    ):
        yield

app = FastAPI(lifespan=lifespan)
```

-  Auto-applies migrations locally
-  Creates backups
-  Skipped in production
-  Detailed logging

### Pattern 3: Hybrid - Dev Migrates, Prod Checks

Different behavior per environment:

```python
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    is_dev = os.getenv("ENVIRONMENT", "").lower() in ["dev", "development", "local"]
    
    async with migration_context(
        mode="migrate" if is_dev else "check",
        all_databases=True,
        fail_fast=True,
    ):
        yield

app = FastAPI(lifespan=lifespan)
```

-  Migrates automatically in dev
-  Only checks in production
-  One configuration for all environments

### Pattern 4: No Checks (CI/CD Handles It)

If you run migrations in a separate job:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # No migration_context - migrations handled by CI/CD
    yield
    # Just cleanup on shutdown if needed

app = FastAPI(lifespan=lifespan)
```

Use this when:
- Migrations run in Kubernetes init containers
- CI/CD applies migrations before deployment
- You use tools like Flyway or Liquibase

## Direct Helper Functions

If you don't want to use `migration_context`, you can call the helpers directly:

### `check_schema_on_startup`

Read-only validation:

```python
from dbwarden.fastapi import check_schema_on_startup

@asynccontextmanager
async def lifespan(app: FastAPI):
    results = check_schema_on_startup(
        all_databases=True,
        fail_fast=True,
    )
    # results is a list of HealthResult objects
    yield
```

**Function signature:**

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
) -> list[HealthResult]:
    """Run read-only startup schema checks."""
```

**Returns:** List of `HealthResult` objects with health status per database.

### `migrate_on_startup`

Apply migrations:

```python
from dbwarden.fastapi import migrate_on_startup

@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate_on_startup(
        all_databases=True,
        with_backup=True,
        only_dev=True,
    )
    yield
```

**Function signature:**

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
) -> None:
    """Run migration workflow at startup."""
```

Use these when you need more control or want to access the health results. For most cases, `migration_context` is simpler.

## Error Handling

### Connection Errors

If database is unreachable:

```
RuntimeError: Startup check failed: primary: could not connect to server: 
Connection refused (host:5432)
```

**Solution:**
- Check database is running
- Verify connection URL
- Check network/firewall
- Ensure credentials are correct

### Pending Migrations

If migrations are pending and `mode="check"`:

```
RuntimeError: Startup check failed: primary: 3 pending migrations
```

**Solution:**
```bash
# Apply migrations manually
$ dbwarden migrate

# Or use migrate mode
# migration_context(mode="migrate")
```

### Production Migration Blocked

If you try `mode="migrate"` in production:

```
RuntimeError: migrate_on_startup is blocked in production unless 
allow_in_production=True
```

**Solution:**
- Run migrations in a separate job
- Or add `allow_in_production=True` (not recommended)

### Multiple Databases, One Fails

If `all_databases=True` and one database fails:

```
RuntimeError: Startup check failed: primary: ok; analytics: connection refused
```

The app exits even if some databases are healthy. Fix all databases before starting.

## Comparison: Check vs Migrate

| | **Check Mode** | **Migrate Mode** |
|---|---|---|
| **Reads schema** |  |  |
| **Checks connectivity** |  |  |
| **Reports pending migrations** |  |  |
| **Applies migrations** |  |  |
| **Modifies database** |  |  |
| **Production safe (multi-pod)** |  |  Risky |
| **Can rollback** | N/A |  |
| **Requires lock** |  |  |
| **Fast** |  (< 100ms) |  Depends on migrations |

## Environment Detection

DBWarden detects your environment from the `ENVIRONMENT` variable:

### Development Environments

Detected as "development":
- `dev`
- `development`
- `local`
- `test`
- `testing`

```bash
export ENVIRONMENT=development
```

### Production Environments

Detected as "production":
- `prod`
- `production`

```bash
export ENVIRONMENT=production
```

### Why It Matters

Some parameters behave differently based on environment:

**`only_dev=True`**  Skipped in production
**`allow_in_production=False`**  Migrate mode blocked in production

## Troubleshooting

### App Starts But Migrations Not Checked

Check that `migration_context` is actually running:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan starting...")  # Debug
    async with migration_context(mode="check", verbose=True):
        print("Passed checks!")  # Debug
        yield
    print("Lifespan ending...")  # Debug
```

Make sure you're passing `lifespan` to `FastAPI`:

```python
#  Correct
app = FastAPI(lifespan=lifespan)

#  Wrong - lifespan not used
app = FastAPI()
```

### Checks Pass But Routes Fail

If startup checks pass but routes fail with connection errors:

1. **Different databases?** - Startup checks one database, routes use another
2. **Connection pool exhausted?** - Too many concurrent requests
3. **Database restarted?** - Connection was valid at startup but not now

### Slow Startup

If startup is slow:

1. **Migrations taking time?** - Use `mode="check"` instead of `mode="migrate"`
2. **Multiple databases?** - Each one adds latency
3. **Network latency?** - Database is far away
4. **First connection slow?** - Normal for some databases (initial SSL handshake)

Use `verbose=True` to see timing:

```python
async with migration_context(mode="check", verbose=True):
    yield
```

### Production Blocked

If you see "blocked in production" errors:

```python
#  This is blocked
async with migration_context(mode="migrate"):
    yield

#  Solutions:

# 1. Use check mode
async with migration_context(mode="check"):
    yield

# 2. Use only_dev
async with migration_context(mode="migrate", only_dev=True):
    yield

# 3. Override (not recommended)
async with migration_context(mode="migrate", allow_in_production=True):
    yield
```

## What's Next?

- **[Complete Application](complete-application.md)** - Full working example
- **[Health Endpoints](health-endpoints.md)** - Runtime health monitoring
- **[Production Patterns](../advanced/production-patterns.md)** - K8s, CI/CD strategies
- **[Multi-Database](../advanced/multi-database.md)** - Multiple databases
