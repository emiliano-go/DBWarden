# DBWarden 0.6 Release Notes

**Release Date:** April 2026

---

## Overview

DBWarden 0.6 introduces **first-class FastAPI integration** and a **complete documentation overhaul** following the excellent FastAPI documentation style. This release brings database sessions, health endpoints, and migration checks directly into your FastAPI applications with minimal boilerplate.

---

## major Features

### FastAPI Integration

A new `dbwarden[fastapi]` extra provides:

#### `get_session()` - Async Database Sessions

Get SQLAlchemy `AsyncSession` dependencies in your routes with proper lifecycle management:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dbwarden.fastapi import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session())]

@app.get("/users")
async def list_users(session: SessionDep):
    result = await session.execute(select(User))
    return result.scalars().all()
```

**Features:**
- Automatic engine creation and caching
- Request-scoped sessions
- Automatic cleanup and error handling
- Multi-database support
- Dev mode support (`get_session(dev=True)`)

#### `migration_context()` - Startup Validation

Validate database connectivity and migration state at app startup:

```python
from contextlib import asynccontextmanager
from dbwarden.fastapi import migration_context

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check"):
        yield

app = FastAPI(lifespan=lifespan)
```

**Modes:**
- `mode="check"`: Validate connectivity and migration state (recommended for production)
- `mode="migrate"`: Auto-apply migrations on startup (development only)

#### `DBWardenHealthRouter()` - Health Endpoints

Production-ready database health monitoring:

```python
from dbwarden.fastapi import DBWardenHealthRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Provides:
- `GET /health/` - Overall health for all databases
- `GET /health/{database_name}` - Per-database health
- Database connectivity checks
- Migration state monitoring
- Kubernetes probe-ready responses

---

## Installation

```bash
pip install dbwarden[fastapi]
```

---

## Complete Documentation Overhaul

Following [FastAPI's documentation style](https://fastapi.tiangolo.com), the documentation has been reorganized into a comprehensive learning resource.

### FastAPI Documentation (`docs/fastapi/`)

```
fastapi/
├── index.md                    # Landing page
├── concepts.md                 # High-level concepts
├── reference.md               # Complete API reference
├── tutorial/
│   ├── first-steps.md         # 2-minute quick start
│   ├── session-dependency.md # Deep dive on get_session
│   ├── startup-checks.md    # migration_context
│   ├── health-endpoints.md   # Health router
│   └── complete-application.md
└── advanced/
    ├── multi-database.md
    ├── testing.md
    ├── transaction-management.md
    ├── engine-lifecycle.md
    └── production-patterns.md
```

**New Content:**
- ~3,000 lines of comprehensive documentation
- Progressive learning path (beginner → advanced)
- Real-world production patterns
- Testing guides with pytest fixtures
- Kubernetes deployment examples
- Troubleshooting sections

### Configuration Documentation (`docs/configuration/`)

```
configuration/
├── index.md                   # Landing page
├── quick-start.md             # Your first configuration
├── concepts.md               # How configuration works
├── connection-urls.md         # Database URL formats
├── model-discovery.md         # How model_paths works
├── dev-mode.md             # Local development
├── multi-database.md        # Multiple databases
├── production-patterns.md   # Real-world examples
└── troubleshooting.md       # Common issues
```

**New Content:**
- ~3,800 lines of documentation
- Connection URL reference for PostgreSQL, SQLite, MySQL, ClickHouse
- Environment variable patterns
- Docker and Kubernetes integration
- AWS RDS and Secrets Manager integration

---

## Changes

### New CLI Commands

None - this release focuses on the FastAPI integration module.

### Breaking Changes

None - all existing functionality is preserved.

### Deprecations

The old FastAPI documentation files are now redirects:
- `fastapi/get-session.md` → redirects to `fastapi/tutorial/session-dependency.md`
- `fastapi/migration-context.md` → redirects to `fastapi/tutorial/startup-checks.md`
- `fastapi/health-router.md` → redirects to `fastapi/tutorial/health-endpoints.md`
- `fastapi/full-example.md` → redirects to `fastapi/tutorial/complete-application.md`

---

## Upgrading

### From 0.5

1. Install the FastAPI extra:
   ```bash
   pip install dbwarden[fastapi]
   ```

2. Add session dependency to your routes (optional):
   ```python
   from dbwarden.fastapi import get_session
   
   SessionDep = Annotated[AsyncSession, Depends(get_session())]
   ```

3. Add startup checks (recommended):
   ```python
   from dbwarden.fastapi import migration_context
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       async with migration_context(mode="check"):
           yield
   ```

4. Add health endpoints (optional):
   ```python
   from dbwarden.fastapi import DBWardenHealthRouter
   
   app.include_router(DBWardenHealthRouter(), prefix="/health")
   ```

---

## What's Next

Possible future additions:
- Async session with explicit transaction management
- WebSocket support
- GraphQL integration examples
- More database backends (async CockroachDB support)

---

## Thank You

Thanks to all contributors and users of DBWarden. Special thanks to the FastAPI community for the excellent documentation that inspired this overhaul.

---

## Links

- **Documentation:** https://dbwarden.readthedocs.io
- **GitHub:** https://github.com/emiliano-gandini-outeda/dbwarden
- **PyPI:** https://pypi.org/project/dbwarden/