# `get_session`

`get_session` returns a FastAPI dependency that yields `AsyncSession` sourced from DBWarden config.

## Install dependency group

```bash
pip install "dbwarden[fastapi]"
```

## Basic usage

```python
from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import get_session

app = FastAPI()
session_dep = get_session()


@app.get("/users")
async def list_users(session: Annotated[AsyncSession, Depends(session_dep)]):
    result = await session.execute("SELECT 1")
    return {"ok": True}
```

## Multi-database usage

```python
analytics_session = get_session("analytics")
```

## Dev mode usage

```python
dev_session = get_session("primary", dev=True)
```

## Notes

- session factories are cached per resolved async URL
- PostgreSQL and SQLite async drivers are supported out of the box
- unsupported async backends raise clear errors

## Navigation

- Previous: [Overview](overview.md)
- Next: [migration_context](migration-context.md)
