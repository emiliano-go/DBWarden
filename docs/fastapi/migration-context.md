# `migration_context`

`migration_context` is a FastAPI lifespan helper for startup migration or read-only schema checks.

Related direct helpers:

- `check_schema_on_startup(...)`
- `migrate_on_startup(...)`

## Modes

- `mode="migrate"`: run migration workflow at startup
- `mode="check"`: validate connectivity/schema state without mutation

## Usage in lifespan

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from dbwarden.fastapi import migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", all_databases=True, fail_fast=True):
        yield


app = FastAPI(lifespan=lifespan)
```

## Important options

- `database`, `all_databases`
- `dev`, `strict_translation`
- `with_backup`, `backup_dir`
- `allow_in_production`
- `fail_fast`
- `only_dev`

## `only_dev` behavior

If `only_dev=True`, helper logic runs only when `ENVIRONMENT` is one of:

- `dev`
- `development`
- `local`
- `test`
- `testing`

Otherwise startup helper logic is skipped.

## Production guidance

- use `mode="check"` in app startup by default
- run `mode="migrate"` in controlled rollout jobs unless intentionally allowed in production

## Navigation

- Previous: [get_session](get-session.md)
- Next: [DBWardenHealthRouter](health-router.md)
