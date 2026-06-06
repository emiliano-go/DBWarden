# `get_session`

!!! note "Page Moved"
    This page has been moved and significantly expanded with better examples and explanations.

##  New Location

**[ Session Dependency Tutorial](tutorial/session-dependency.md)**

The new page includes:
- Progressive examples from simple to advanced
- Recommended patterns with type aliases
- Complete lifecycle explanations
- Multi-database usage
- Testing patterns
- Troubleshooting guide

---

For quick reference, here's the basic usage:

## Quick Reference

`get_session` provides a FastAPI-native `AsyncSession` dependency that sources its connection from the DBWarden config registry. You never need to manually build an engine, session factory, or connection string in your FastAPI app  `get_session` owns that entirely.

## Install dependency group

```bash
pip install "dbwarden[fastapi]"
```

## Function signature

```python
def get_session(
    database: str | None = None,
    *,
    dev: bool = False,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Return a FastAPI dependency that yields AsyncSession.
    
    Args:
        database: Database name from config. If None, uses the default database.
        dev: If True, uses dev_database_url instead of database_url.
    
    Returns:
        A callable dependency that FastAPI's Depends() can consume.
    """
```

## Recommended pattern: Define type aliases in config

For cleaner route signatures, define type aliases once in your application config:

```python
# config.py or dependencies.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

# Single-database projects (uses default database)
SessionDep = Annotated[AsyncSession, Depends(get_session())]

# Multi-database projects (targets specific database by name)
AnalyticsSessionDep = Annotated[AsyncSession, Depends(get_session("analytics"))]
```

Then use them in your routes:

```python
from fastapi import FastAPI
from sqlalchemy import select
from .config import SessionDep
from .models import User

app = FastAPI()


@app.get("/users")
async def list_users(session: SessionDep):
    result = await session.execute(select(User))
    return result.scalars().all()
```

## How it works

**Calling `get_session` with no arguments returns a dependency that yields a session for the default database:**

```python
# Returns dependency for default database
session_dep = get_session()
```

**Calling `get_session("analytics")` returns a dependency for the "analytics" database:**

```python
# Returns dependency for "analytics" database
analytics_dep = get_session("analytics")
```

Both forms return a callable that FastAPI's `Depends()` can consume directly. The return type is always `AsyncSession`  DBWarden is async-native for FastAPI.

## Engine and session lifecycle

**Engine creation:**
- Engines are created once per database per process, on first request
- Engines are cached for the lifetime of the application
- Engine cache is keyed by the resolved async database URL
- Engines are built from `database_url` (or `dev_database_url` if `dev=True`) resolved from the DBWarden config registry

**Session factory:**
- One `async_sessionmaker` per unique async URL, cached per process
- Sessions use `expire_on_commit=False` by default  this is the correct default for FastAPI response models, where you need to access attributes after `commit()`

**Session scope:**
- One session per request
- Session is opened when the dependency is invoked
- Session is yielded to the route function
- Session is automatically closed in a `finally` block
- If an exception occurs in your route, the session is rolled back before the exception propagates

## Dev mode usage

If you pass `dev=True`, the session uses `dev_database_url` from your config instead of `database_url`:

```python
# In your config or test fixtures
DevSessionDep = Annotated[AsyncSession, Depends(get_session(dev=True))]
```

This is useful for running your app against a local dev database without changing route code.

## Multi-database usage

For projects with multiple databases, define separate type aliases for each:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

# Primary database (default)
PrimarySessionDep = Annotated[AsyncSession, Depends(get_session())]

# Analytics database
AnalyticsSessionDep = Annotated[AsyncSession, Depends(get_session("analytics"))]

# Logging database
LoggingSessionDep = Annotated[AsyncSession, Depends(get_session("logging"))]
```

Then use them in routes that need multiple databases:

```python
@app.get("/analytics/report")
async def get_report(
    primary_session: PrimarySessionDep,
    analytics_session: AnalyticsSessionDep,
):
    # Query both databases in the same request
    users = await primary_session.execute(select(User))
    events = await analytics_session.execute(select(Event))
    return {"users": users.scalars().all(), "events": events.scalars().all()}
```

## Supported databases

- **PostgreSQL**: Automatically uses `postgresql+asyncpg` driver
- **SQLite**: Automatically uses `sqlite+aiosqlite` driver

If your config URL doesn't include a driver (e.g., `postgresql://...`), DBWarden automatically upgrades it to the async version. If you specify a driver explicitly (e.g., `postgresql+asyncpg://...`), DBWarden uses it as-is.

Unsupported database types raise a clear `ValueError` with instructions.

## Error handling

- **Connection errors**: SQLAlchemy `OperationalError` propagates naturally  let FastAPI's exception handling catch it
- **Route exceptions**: Session is automatically rolled back, then exception re-raises
- **Database not found**: If you pass a database name that doesn't exist in config, `get_database()` raises an error at engine creation time

## Notes

- Session factories are cached per resolved async URL  multiple calls to `get_session()` reuse the same factory
- The `expire_on_commit=False` setting means you can safely access model attributes after committing, which is essential for FastAPI response models
- Never call `session.commit()` or `session.rollback()` manually in your route unless you have a specific reason  let the dependency handle lifecycle

## Navigation

- Previous: [Overview](overview.md)
- Next: [migration_context](migration-context.md)
