# Session Dependency

Learn how to use `get_session()` to get database sessions in your FastAPI routes.

## What is `get_session`?

`get_session()` is a function that returns a **FastAPI dependency**. That dependency gives you a SQLAlchemy `AsyncSession` in your routes.

You never need to:
- Manually create engines
- Build session factories
- Manage session lifecycle
- Write cleanup code

DBWarden handles all of that for you.

## Quick Example

Here's the simplest possible example:

```python
from typing import Annotated
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

app = FastAPI()

# Create a dependency
SessionDep = Annotated[AsyncSession, Depends(get_session())]

@app.get("/users")
async def list_users(session: SessionDep):
    # Use the session
    result = await session.execute(select(User))
    return result.scalars().all()
```

That's it! **3 steps**:
1. Import `get_session`
2. Create a type alias with `Annotated`
3. Use it in your route parameters

## Recommended Pattern

For cleaner code, define your session dependency **once** in a config or dependencies file:

```python
# app/dependencies.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session())]
```

Then import and use it in your routes:

```python
# app/routes/users.py
from fastapi import APIRouter
from sqlalchemy import select
from app.dependencies import SessionDep
from app.models import User

router = APIRouter()

@router.get("/users")
async def list_users(session: SessionDep):
    result = await session.execute(select(User))
    return result.scalars().all()

@router.get("/users/{user_id}")
async def get_user(user_id: int, session: SessionDep):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
```

!!! tip "One Definition, Many Uses"
    Define `SessionDep` once and reuse it across all your route files. This keeps your code DRY and makes refactoring easier.

## How It Works

Let's understand what happens when you use `get_session()`:

### 1. First Request

When the first request comes in:

```python
@app.get("/users")
async def list_users(session: SessionDep):
    # Request arrives here ⬇️
    ...
```

1. **FastAPI calls the dependency** - The `get_session()` dependency runs
2. **Engine is created** - DBWarden creates an async engine from your config
3. **Engine is cached** - The engine is stored in memory for reuse
4. **Session factory is created** - An `async_sessionmaker` is created
5. **New session opens** - A fresh session is created for this request
6. **Session is yielded** - Your route function receives the session
7. **Route executes** - Your code runs with the session
8. **Session closes** - The session is automatically closed in a `finally` block

### 2. Subsequent Requests

On every request after the first:

1. **FastAPI calls the dependency** - The `get_session()` dependency runs
2. **Cached engine is reused** - No new engine is created
3. **New session opens** - A fresh session for this request
4. **Session is yielded** - Your route gets the session
5. **Route executes** - Your code runs
6. **Session closes** - Automatic cleanup

!!! info "Engine Caching"
    Engines are created **once per database** and cached for the application lifetime. This is efficient and follows SQLAlchemy best practices.

## Function Signature

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

### Parameters

**`database`** (optional)
- The name of the database from your DBWarden config
- If not provided, uses the default database
- Example: `get_session("analytics")`

**`dev`** (optional, keyword-only)
- If `True`, uses `dev_database_url` instead of `database_url`
- Useful for local development and testing
- Default: `False`
- Example: `get_session(dev=True)`

## Single Database Projects

Most projects have one database. For these, define a simple `SessionDep`:

```python
# app/dependencies.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

# Uses the default database
SessionDep = Annotated[AsyncSession, Depends(get_session())]
```

Use it everywhere:

```python
@app.get("/users")
async def list_users(session: SessionDep):
    ...

@app.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    ...

@app.get("/products")
async def list_products(session: SessionDep):
    ...
```

## Multi-Database Projects

If you have multiple databases, create a type alias for each:

```python
# app/dependencies.py
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

Then use the appropriate dependency in each route:

```python
@app.get("/users")
async def list_users(session: PrimarySessionDep):
    # Uses primary database
    result = await session.execute(select(User))
    return result.scalars().all()

@app.get("/analytics/events")
async def list_events(session: AnalyticsSessionDep):
    # Uses analytics database
    result = await session.execute(select(Event))
    return result.scalars().all()
```

### Query Multiple Databases

You can use multiple session dependencies in the same route:

```python
@app.get("/analytics/report")
async def get_report(
    primary_session: PrimarySessionDep,
    analytics_session: AnalyticsSessionDep,
):
    # Query primary database
    users = await primary_session.execute(select(User))
    
    # Query analytics database
    events = await analytics_session.execute(select(Event))
    
    return {
        "users": users.scalars().all(),
        "events": events.scalars().all(),
    }
```

Each session is independent and properly managed.

## Dev Mode

During development, you might want to use a different database (like SQLite instead of PostgreSQL).

Configure a dev database in your DBWarden config:

```python
# dbwarden.py
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost/prod",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
    model_paths=["app.models"],
)
```

Then create a dev session dependency:

```python
# app/dependencies.py
DevSessionDep = Annotated[AsyncSession, Depends(get_session(dev=True))]
```

Or set environment variables to automatically use dev mode:

```bash
export ENVIRONMENT=development
```

Then `get_session()` will automatically use `dev_database_url`.

## Session Lifecycle

### Request-Scoped Sessions

Each request gets its own session:

```python
@app.get("/users")
async def list_users(session: SessionDep):
    # Fresh session for this request
    result = await session.execute(select(User))
    return result.scalars().all()
    # Session automatically closes here
```

Sessions are **never shared** between requests. This prevents:
- Thread safety issues
- Transaction isolation problems
- Stale data

### Automatic Cleanup

Sessions are closed automatically, even if errors occur:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    
    if user.email == "invalid":
        raise ValueError("Invalid email")  # Session still closes!
    
    await session.commit()
    return user
```

The session closes in a `finally` block, so cleanup always happens.

### Error Handling

If an error occurs in your route, the session is automatically rolled back:

```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()  # Database error occurs here
    # Session is rolled back automatically
    # Error propagates to FastAPI's error handling
    return user
```

You don't need to write `try/except` blocks for session rollback.

## Session Settings

Sessions created by `get_session()` use these settings:

```python
async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # ⭐ Important for FastAPI
)
```

### `expire_on_commit=False`

This setting is crucial for FastAPI response models.

**Without it:**
```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()
    
    # ❌ This would fail - attributes expired after commit
    return user
```

**With it:**
```python
@app.post("/users")
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()
    
    # ✅ This works - attributes still accessible
    return user
```

## Supported Databases

DBWarden automatically uses async drivers for:

### PostgreSQL

Uses `postgresql+asyncpg` driver:

```python
# Your config can use any of these:
database_url_sync="postgresql://user:password@localhost/db"
database_url_sync="postgresql+asyncpg://user:password@localhost/db"
database_url_sync="postgres://user:password@localhost/db"
```

DBWarden automatically upgrades to `postgresql+asyncpg://...`

### SQLite

Uses `sqlite+aiosqlite` driver:

```python
# Your config can use any of these:
database_url_sync="sqlite:///./app.db"
database_url_sync="sqlite+aiosqlite:///./app.db"
```

DBWarden automatically upgrades to `sqlite+aiosqlite://...`

### Unsupported Databases

If you try to use an unsupported database type, you'll get a clear error:

```
ValueError: get_session currently supports async PostgreSQL and SQLite drivers. 
Unsupported database_type: mysql
```

!!! info "Driver Installation"
    Make sure you have the appropriate async driver installed:
    - PostgreSQL: `pip install asyncpg`
    - SQLite: `pip install aiosqlite`

## Common Patterns

### Creating Records

```python
@app.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate, session: SessionDep):
    user = User(**user_data.dict())
    session.add(user)
    await session.commit()
    await session.refresh(user)  # Load generated fields
    return user
```

### Updating Records

```python
@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: SessionDep,
):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    for key, value in user_data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    await session.commit()
    await session.refresh(user)
    return user
```

### Deleting Records

```python
@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, session: SessionDep):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(404, "User not found")
    
    await session.delete(user)
    await session.commit()
```

### Querying with Filters

```python
@app.get("/users", response_model=list[UserResponse])
async def list_users(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    active: bool | None = None,
):
    stmt = select(User).offset(skip).limit(limit)
    
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    
    result = await session.execute(stmt)
    return result.scalars().all()
```

## Troubleshooting

### "RuntimeError: Working outside of application context"

This happens if you call `get_session()` at module level:

```python
# ❌ Wrong - called at module level
SessionDep = Annotated[AsyncSession, Depends(get_session())]
session = SessionDep()  # Error!
```

Solution: Only use `SessionDep` as a FastAPI dependency:

```python
# ✅ Correct - used as dependency
@app.get("/users")
async def list_users(session: SessionDep):
    ...
```

### "Config not loaded"

If DBWarden config hasn't been loaded, you'll get an error. Make sure your `dbwarden.py` file is imported before FastAPI starts:

```python
# main.py
import dbwarden  # Load config first
from fastapi import FastAPI
```

Or ensure DBWarden auto-discovery is working.

### "Cannot connect to database"

If the database is unreachable, you'll get a SQLAlchemy `OperationalError`. This happens on the first request that needs the database.

Check:
- Is the database running?
- Is the connection URL correct?
- Are credentials valid?
- Is the network reachable?

### "expire_on_commit" Errors

If you see errors about accessing attributes after commit, check that you're using DBWarden's `get_session()` and not creating sessions manually.

DBWarden sessions use `expire_on_commit=False` by default.

## Recap

You learned:

✅ `get_session()` returns a FastAPI dependency for database sessions  
✅ Define `SessionDep` once and reuse it across routes  
✅ Sessions are request-scoped and automatically cleaned up  
✅ Use different dependencies for multi-database projects  
✅ Engines are created once and cached per database  
✅ `expire_on_commit=False` makes FastAPI response models work correctly  
✅ PostgreSQL and SQLite are supported with automatic async driver selection  

## What's Next?

- **[Startup Checks](startup-checks.md)** - Validate your database on app boot
- **[Transaction Management](../advanced/transaction-management.md)** - Manual commits and rollbacks
- **[Testing](../advanced/testing.md)** - Override dependencies in tests
- **[Engine Lifecycle](../advanced/engine-lifecycle.md)** - Caching, pooling, disposal
