# FastAPI Integration Overview

DBWarden's FastAPI integration gives you a complete runtime layer that stays aligned with your migration config.

Instead of maintaining one config path for migrations and another for app runtime, you use one DBWarden configuration source and consume it across startup, health, and request dependencies.

## Core components

- `get_session(...)`: async SQLAlchemy session dependency from DBWarden config
- `migration_context(...)`: lifespan helper for startup migration/check modes
- `DBWardenHealthRouter()`: mountable health endpoints for DB and migration state

Additional startup helpers:

- `check_schema_on_startup(...)`: read-only startup checks
- `migrate_on_startup(...)`: controlled startup migration execution

## Why this exists

Without integration helpers, teams often split configuration:

- DBWarden config for migrations
- custom app code for engines/sessions/startup checks

This module keeps those concerns unified around one DBWarden config source.

## The full picture

1. Define databases once with `database_config(...)`
2. Use `migration_context(...)` during FastAPI lifespan startup
3. Use `get_session(...)` for route-level `AsyncSession` dependencies
4. Mount `DBWardenHealthRouter()` for operational visibility

This gives a single path from schema definition to runtime health.

## Install

```bash
pip install "dbwarden[fastapi]"
```

Use latest FastAPI-compatible stack in your app environment.

## Integration picture

1. DBWarden resolves configured databases from `database_config(...)`
2. `get_session(...)` provides request-scoped `AsyncSession`
3. `migration_context(...)` runs startup checks or migrations
4. `DBWardenHealthRouter()` exposes runtime health endpoints

## Startup modes

`migration_context(mode="check")`

- validates DB connectivity and migration state
- does not mutate schema/data
- recommended default for production app startup

`migration_context(mode="migrate")`

- runs migration workflow on startup
- can be gated with `allow_in_production` and `only_dev`
- useful for controlled local/dev environments

## only_dev behavior

Both `check_schema_on_startup(...)` and `migrate_on_startup(...)` support `only_dev=True`.

When enabled, helper execution is skipped unless `ENVIRONMENT` indicates a development context (`dev`, `development`, `local`, `test`, `testing`).

## Recommended production pattern

- prefer migration jobs in CI/CD or orchestration before app rollout
- use `migration_context(mode="check")` in app startup
- use health router endpoints for readiness/observability

## Minimal wiring example

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from dbwarden.fastapi import DBWardenHealthRouter, migration_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_context(mode="check", all_databases=True, fail_fast=True):
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(DBWardenHealthRouter(), prefix="/health")
```

## Navigation

- Next: [get_session](get-session.md)
