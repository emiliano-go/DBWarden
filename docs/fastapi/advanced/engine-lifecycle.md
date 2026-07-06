---
{}
---

# Engine Lifecycle

Learn how DBWarden manages database engines and connections.

## How Engines Are Created

When you first use a session annotation like `primary.async_session`:

1. **First request arrives** with a session parameter annotation
2. **DBWarden checks engine cache** - Is there an engine for this database?
3. **If not cached:**
   - Reads database config from DBWarden registry
   - Converts URL to async version (`postgresql+asyncpg://...`)
   - Creates `AsyncEngine` with `create_async_engine()`
   - Caches engine by database URL
4. **Creates session factory** (`async_sessionmaker`)
5. **Opens new session** for this request
6. **Yields session** to your route
7. **Closes session** in finally block

### Engine Caching

Engines are cached per unique database URL:

```python
# Internal cache (simplified)
_engine_cache = {}

def get_engine(database_url: str):
    if database_url not in _engine_cache:
        _engine_cache[database_url] = create_async_engine(database_url)
    return _engine_cache[database_url]
```

**Why cache engines?**
- Engines are expensive to create
- Each engine manages a connection pool
- Creating per-request would exhaust connections
- Single engine per database is SQLAlchemy best practice

## Connection Pooling

Each engine maintains a connection pool:

### Default Pool Settings

```python
create_async_engine(
    database_url,
    pool_size=5,          # Max connections in pool
    max_overflow=10,      # Extra connections if pool full
    pool_timeout=30,      # Wait time for available connection
    pool_recycle=3600,    # Recycle connections after 1 hour
)
```

### Custom Pool Settings

To customize, you need to create engines manually (advanced):

```python
from sqlalchemy.ext.asyncio import create_async_engine

custom_engine = create_async_engine(
    "postgresql+asyncpg://...",
    pool_size=20,         # More connections
    max_overflow=5,       # Fewer overflow
    pool_pre_ping=True,   # Test connections before use
)
```

DBWarden uses SQLAlchemy's defaults, which work well for most applications.

## Engine Disposal

Engines should be disposed when your app shuts down.

### Using `dispose_engines`

DBWarden provides a built-in `dispose_engines()` function that closes all cached engines and clients:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dbwarden.fastapi import dispose_engines


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    dispose_engines()


app = FastAPI(lifespan=lifespan)
```

This closes async and sync session factories, connection pools, and ClickHouse clients for all configured databases.

In Kubernetes, pods are terminated quickly, so disposal is less critical. The OS cleans up connections. However, calling `dispose_engines()` is still recommended for clean shutdowns.

## Session Lifecycle

Each request gets its own session:

```
Request → get_session() → Session created → Route runs → Session closed
```

### Session Settings

DBWarden sessions use:

```python
async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Keep objects accessible after commit
)
```

### Why `expire_on_commit=False`?

**Without it:**
```python
@app.post("/users")
async def create_user(session: primary.async_session):
    user = User(email="test@example.com")
    session.add(user)
    await session.commit()
    
    #  Error: Instance is not bound to a Session
    return user
```

**With it:**
```python
@app.post("/users")
async def create_user(session: primary.async_session):
    user = User(email="test@example.com")
    session.add(user)
    await session.commit()
    
    #  Works: Object still accessible
    return user
```

FastAPI needs to serialize the object after the route returns, so `expire_on_commit=False` is essential.

## Connection Pool Exhaustion

### Symptoms

```
TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

This happens when:
- Too many concurrent requests
- Connections not being released
- Long-running queries
- Connection leaks

### Solutions

#### 1. Increase Pool Size

```python
# In engine creation
pool_size=20,
max_overflow=10,
```

#### 2. Profile Connection Usage

```python
# Enable pool logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
```

#### 3. Close Connections Properly

Make sure sessions close:

```python
#  Correct - session closes automatically
@app.get("/users")
async def list_users(session: primary.async_session):
    result = await session.execute(select(User))
    return result.scalars().all()
    # Session closes here

#  Wrong - keeping session reference
_sessions = []

@app.get("/users")
async def list_users(session: primary.async_session):
    _sessions.append(session)  # Leak!
    ...
```

#### 4. Set Connection Timeout

```python
pool_timeout=30,  # Wait 30 seconds for connection
```

## Engine Per Database

With multiple databases, each gets its own engine:

```python
# Internal (simplified)
_engine_cache = {
    "postgresql://localhost/primary": <Engine1>,
    "postgresql://localhost/analytics": <Engine2>,
    "postgresql://localhost/logging": <Engine3>,
}
```

Each engine has its own connection pool.

## Monitoring Connections

### Check Pool Status

```python
from sqlalchemy import inspect

@app.get("/debug/pool-status")
async def pool_status():
    engine = get_engine_for_database("primary")  # Hypothetical
    pool = engine.pool
    
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }
```

### Log Pool Events

```python
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)
```

## Connection Recycling

Connections are recycled after `pool_recycle` seconds (default: -1, never):

```python
create_async_engine(
    database_url,
    pool_recycle=3600,  # Recycle after 1 hour
)
```

**Why recycle?**
- Database closes idle connections
- Prevents stale connections
- Refreshes connection state

## Pre-Ping

Test connections before use:

```python
create_async_engine(
    database_url,
    pool_pre_ping=True,  # Test connection with SELECT 1
)
```

**Trade-off:**
- Pro: Prevents errors from stale connections
- Con: Adds latency to every request

## What's Next?

- **[Production Patterns](production-patterns.md)** - Deploy and monitor
- **[Multi-Database](multi-database.md)** - Multiple connection pools
