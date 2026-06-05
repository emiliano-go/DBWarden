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
- **DBWarden configured** (see [Configuration](../../configuration.md))

If you haven't configured DBWarden yet, create a `dbwarden.py` file:

```python
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
    model_paths=["app.models"],
)
```

## Install

Install DBWarden with the FastAPI extra:

```bash
pip install "dbwarden[fastapi]"
```

This installs DBWarden along with FastAPI-specific dependencies.

## Create Your First App

### Step 1: Import

Create a file `main.py`:

```python
from fastapi import FastAPI
from dbwarden.fastapi import migration_context
from contextlib import asynccontextmanager
```

### Step 2: Add Lifespan

Add a lifespan function to check migrations on startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield
```

This runs a migration check when your app starts. If migrations are pending or the database is unreachable, the app won't start.

### Step 3: Create the App

```python
app = FastAPI(lifespan=lifespan)
```

### Step 4: Add a Route

Let's add a simple route that uses the database:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

# Create a type alias for cleaner code
SessionDep = Annotated[AsyncSession, Depends(get_session())]

@app.get("/")
async def root(session: SessionDep):
    # Execute a simple query
    result = await session.execute(text("SELECT 'Hello from DBWarden!' as message"))
    row = result.first()
    return {"message": row.message}
```

### Complete File

Here's the complete `main.py`:

```python
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import get_session, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)

SessionDep = Annotated[AsyncSession, Depends(get_session())]


@app.get("/")
async def root(session: SessionDep):
    result = await session.execute(text("SELECT 'Hello from DBWarden!' as message"))
    row = result.first()
    return {"message": row.message}
```

That's it! **Less than 25 lines** including imports.

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
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import DBWardenHealthRouter, get_session, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")

SessionDep = Annotated[AsyncSession, Depends(get_session())]


@app.get("/")
async def root(session: SessionDep):
    result = await session.execute(text("SELECT 'Hello from DBWarden!' as message"))
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

### `get_session()`

- Returns a FastAPI dependency
- Creates database sessions automatically
- One session per request
- Automatically closes sessions after the request

### `SessionDep` Type Alias

- Makes your code cleaner
- Type hints for better IDE support
- Reusable across all your routes

### `DBWardenHealthRouter()`

- Adds `/health/` endpoint for all databases
- Adds `/health/{database_name}` for specific database
- Returns connectivity and migration status
- Perfect for Kubernetes probes

## Recap

You learned how to:

✅ Install DBWarden with FastAPI support  
✅ Create a lifespan function for startup checks  
✅ Use `SessionDep` to get database sessions in routes  
✅ Add health endpoints for monitoring  
✅ Run and test your application

## What's Next?

Now that you have a working app, learn more about each component:

- **[Session Dependency](session-dependency.md)** - Deep dive into `get_session()`
- **[Startup Checks](startup-checks.md)** - All about `migration_context()`
- **[Health Endpoints](health-endpoints.md)** - Complete health monitoring guide

Or jump to:

- **[Complete Application](complete-application.md)** - A real-world example with models
- **[Multi-Database](../advanced/multi-database.md)** - Working with multiple databases
