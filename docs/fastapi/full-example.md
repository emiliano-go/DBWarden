# Complete Application Example

!!! note "Page Moved and Expanded"
    This page has been moved and significantly enhanced with more examples.

##  New Location

**[ Complete Application Tutorial](tutorial/complete-application.md)**

The new page includes:
- Full project structure
- Complete CRUD operations
- Pydantic schemas
- Error handling patterns
- Testing examples
- Docker and Kubernetes deployment
- CI/CD pipeline example

---

For quick reference:

## Quick Reference

This is a complete FastAPI app integrating all DBWarden FastAPI helpers.

## `dbwarden.py`

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

## `app/main.py`

```python
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import DBWardenHealthRouter, get_session, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", all_databases=True, fail_fast=True):
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")

session_dep = get_session()


@app.get("/ping-db")
async def ping_db(session: Annotated[AsyncSession, Depends(session_dep)]):
    await session.execute(text("SELECT 1"))
    return {"ok": True}
```

## Run

```bash
uvicorn app.main:app --reload
```

## Endpoints

- `GET /ping-db`
- `GET /health/`
- `GET /health/primary`

## Navigation

- Previous: [DBWardenHealthRouter](health-router.md)
