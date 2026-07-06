---
{}
---

# First Steps

Let's create a FastAPI app with DBWarden in **2 minutes**.

You'll create a simple API with:
- Database sessions in routes
- Startup migration checks
- Health endpoints

## Prerequisites

You should have:

- **Python 3.10+** installed
- **FastAPI** and **uvicorn** installed
- **DBWarden installed** with the FastAPI extra

```bash
uv add "dbwarden[fastapi]"
```

## Create Your First App

Create a single file `main.py`:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from dbwarden import database_config
from dbwarden.fastapi import migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)

primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
    model_paths=["app.models"],
)


@app.get("/")
async def root(session: primary.async_session):
    result = await session.execute(
        text("SELECT 'Hello from DBWarden!' as message")
    )
    row = result.first()
    return {"message": row.message}
```

That's it! **15 lines** of meaningful code including imports.

Key details:
- `database_config()` returns a `DatabaseHandle`
- The handle's `.async_session` is a FastAPI dependency annotation: use it **directly** in route parameters
- No need for `Annotated`, `Depends`, session type aliases, or manual engine creation
- `migration_context(mode="check")` validates the database on startup

## Run It

Start your application:

```bash
uvicorn main:app --reload
```

You'll see output like:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

If there are pending migrations or database issues, the app will fail to start with a clear error message.

## Test It

Open your browser to <http://127.0.0.1:8000>

You'll see:

```json
{
  "message": "Hello from DBWarden!"
}
```

Or use `curl`:

```bash
curl http://127.0.0.1:8000/
```

## Check the Docs

FastAPI automatically generates interactive API documentation.

Open <http://127.0.0.1:8000/docs> to see the Swagger UI with your route.

## Add Health Endpoints

Let's add health checking in **one line**:

```python
from dbwarden.fastapi import DBWardenHealthRouter

# Add this line after creating the app
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Now visit <http://127.0.0.1:8000/health/> to see your database health status:

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

### Complete File with Health

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from dbwarden import database_config
from dbwarden.fastapi import DBWardenHealthRouter, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")

primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
    model_paths=["app.models"],
)


@app.get("/")
async def root(session: primary.async_session):
    result = await session.execute(
        text("SELECT 'Hello from DBWarden!' as message")
    )
    row = result.first()
    return {"message": row.message}
```

## What's Happening?

Let's break down what each piece does:

### `migration_context(mode="check")`

- Runs when your app starts (before accepting requests)
- Checks database connectivity
- Verifies migration state
- Fails fast if there are issues

### `database_config` handle (e.g., `primary`)

- Returns a `DatabaseHandle` with `.async_session` and `.sync_session` properties
- Each property is a FastAPI dependency annotation, usable directly in route parameters
- Create one handle per database, pass the right one to each route

### `primary.async_session`

- A FastAPI dependency annotation with no `Annotated`, `Depends`, or type aliases needed
- Creates a new `AsyncSession` per request automatically
- Closes the session when the request finishes
- For sync routes, use `primary.sync_session` instead

### `DBWardenHealthRouter`

- Adds `/health/` endpoint for all databases
- Adds `/health/{database_name}` for specific database
- Returns connectivity and migration status
- Perfect for Kubernetes probes

## What's Next?

Now that you have a working app, learn more about each component:

- **[Session Dependency](session-dependency.md)** - Deep dive into session handling
- **[Startup Checks](startup-checks.md)** - All about `migration_context()`
- **[Health Endpoints](health-endpoints.md)** - Complete health monitoring guide

Or jump to:

- **[Complete Application](complete-application.md)** - A real-world example with models
- **[Multi-Database](../advanced/multi-database.md)** - Working with multiple databases
