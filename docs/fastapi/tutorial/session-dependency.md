---
{}
---

# Session Dependency

Learn how to get database sessions in your FastAPI routes using `DatabaseHandle`.

## The Handle Pattern

`database_config()` returns a `DatabaseHandle`. Its `.async_session` (and `.sync_session`) properties are FastAPI dependency annotations: use them **directly** in route parameters:

```python
from dbwarden import database_config

primary = database_config(database_name="primary", ...)


@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

No `Annotated`, no `Depends`, no type aliases, no manual session creation.

## Quick Example

```python
from fastapi import FastAPI
from dbwarden import database_config

app = FastAPI()

primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
)


@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
```

That is everything you need:

1. Call `database_config()` and store the handle
2. Use `handle.async_session` as a route parameter type hint
3. FastAPI injects a fresh `AsyncSession` per request

## Recommended Project Structure

For multi-file projects, define the handle in one place and import it:

```python
# dbwarden.py
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/myapp",
    model_paths=["app.models"],
)
```

```python
# app/routes/users.py
from dbwarden import primary
from sqlalchemy import select
from app.models import User

router = APIRouter()

@router.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()

@router.get("/users/{user_id}")
async def get_user(user_id: int, session: primary.async_session):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.post("/users")
async def create_user(user_data: UserCreate, session: primary.async_session):
    user = User(**user_data.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

## How It Works

### 1. First Request

When the first request comes in:

```
1. Route parameter primary.async_session resolves
2. Engine is created from your config
3. Engine is cached for reuse
4. Session factory is created
5. A new AsyncSession opens for this request
6. Your route code runs with the session
7. Session closes automatically when the request finishes
```

### 2. Subsequent Requests

```
1. primary.async_session resolves
2. Cached engine is reused; no new engine created
3. A fresh session opens for this request
4. Your route runs
5. Session closes automatically
```

Engines are created **once per database** and cached for the application lifetime.

## Multi-Database Projects

Create one handle per database:

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/main",
    model_paths=["app.models.primary"],
)

analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://user:password@clickhouse-host:8123/analytics",
    model_paths=["app.models.analytics"],
)

logging = database_config(
    database_name="logging",
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/logs",
    model_paths=["app.models.logging"],
)
```

Use the appropriate handle in each route:

```python
@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()

@app.get("/analytics/events")
async def list_events(session: analytics.async_session):
    result = await session.execute(select(Event))
    return result.scalars().all()
```

### Multiple Sessions in One Route

```python
@app.get("/dashboard")
async def get_dashboard(
    users_session: primary.async_session,
    events_session: analytics.async_session,
):
    users = await users_session.execute(select(User))
    events = await events_session.execute(select(Event))
    return {
        "users": users.scalars().all(),
        "events": events.scalars().all(),
    }
```

Each session is independent and properly managed.

## Sync Sessions

For synchronous route handlers, use `.sync_session`:

```python
@app.get("/report")
def generate_report(session: primary.sync_session):
    result = session.execute(select(Report))
    return result.scalars().all()
```

`.sync_session` works with any sync database driver (psycopg2, mysql-connector, etc.).

## Dev Mode

Configure a dev database and the handle automatically resolves the right URL based on the `ENVIRONMENT` environment variable:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/prod",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
    model_paths=["app.models"],
)
```

- `ENVIRONMENT=development` or `local` or `test`  uses `dev_database_url`
- Otherwise, uses `database_url_sync`

No code changes needed between environments.

## Session Lifecycle

### Request-Scoped Sessions

Each request gets its own session:

```
Request A ── Session A (independent)
Request B ── Session B (independent)
Request C ── Session C (independent)
```

### Automatic Cleanup

Sessions are automatically closed in a `finally` block. You never need manual cleanup.

### Session Settings

DBWarden sessions use `expire_on_commit=False` so that Pydantic response models can access attributes after commit.

## Troubleshooting

### "RuntimeError: Working outside of application context"

This happens if you try to use the session outside a request handler:

```python
# Wrong: used outside a request
session = primary.async_session
```

Solution: only use `primary.async_session` as a **route parameter type hint**:

```python
# Correct
@app.get("/users")
async def list_users(session: primary.async_session):
    ...
```

### "Config not loaded"

Make sure `dbwarden.py` (or whichever file calls `database_config()`) is imported before FastAPI starts:

```python
# main.py
import dbwarden  # Loads config
from fastapi import FastAPI
```

### "Cannot connect to database"

Check:
- Is the database running?
- Is the connection URL correct?
- Are credentials valid?
- Is the network reachable?

### "expire_on_commit" Errors

If you see errors about accessing attributes after commit, ensure you are using the session from the handle (which sets `expire_on_commit=False`).

## Using `get_session` Directly

The `get_session()` function is also available from `dbwarden.fastapi` for advanced cases where you need to create session dependencies dynamically:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

# Named database
SessionDep = Annotated[AsyncSession, Depends(get_session())]
AnalyticsDep = Annotated[AsyncSession, Depends(get_session("analytics"))]

# Dev mode override
DevSessionDep = Annotated[AsyncSession, Depends(get_session(dev=True))]
```

This is useful when:
- You need to override sessions in tests (see [Testing](../advanced/testing.md))
- You want to use the `Annotated` type alias pattern
- You need programmatic database selection at the dependency level

For most cases, the `DatabaseHandle` pattern (`.async_session` / `.sync_session`) is simpler and recommended.

## What's Next?

- **[Startup Checks](startup-checks.md)** - Validate your database on app boot
- **[Transaction Management](../advanced/transaction-management.md)** - Manual commits and rollbacks
- **[Testing](../advanced/testing.md)** - Override dependencies in tests
