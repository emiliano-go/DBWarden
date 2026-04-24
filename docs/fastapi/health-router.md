# `DBWardenHealthRouter`

`DBWardenHealthRouter()` returns a mountable FastAPI `APIRouter` for runtime DB and migration health endpoints.

## Mounting

```python
from fastapi import FastAPI

from dbwarden.fastapi import DBWardenHealthRouter

app = FastAPI()
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

## Routes

- `GET /health/` -> overall health across configured databases
- `GET /health/{database_name}` -> health for one database

## Status codes

- `200` healthy
- `503` degraded/error state
- `404` unknown database on per-db route

## Response schema (simplified)

```json
{
  "status": "ok|degraded|error",
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

## Navigation

- Previous: [migration_context](migration-context.md)
- Next: [Full Example](full-example.md)
