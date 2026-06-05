## DBWarden ClickHouse Expansion Spec

Maintainer: Emiliano Gandini Outeda

Scope: extend DBWarden with stronger ClickHouse support, safer migration workflows, better runtime integration, observability, and reverse-engineering support.

### Branch Split

1. `feature/core-migration-plan-and-config`
2. `feature/core-sandbox-and-dry-run`
3. `feature/core-seeds`
4. `feature/clickhouse-table-features`
5. `feature/clickhouse-objects-and-safety`
6. `feature/fastapi-runtime-expansion`
7. `feature/observability`
8. `feature/cli-enhancements`
9. `feature/generate-models`

### Branch 1: `feature/core-migration-plan-and-config`

Scope:
- Always write a companion `.plan.json` file for every generated migration.
- Support `make-migrations --plan` to emit plan JSON without writing files.
- Allow configuring the migration tracking table name per database.

Requirements:
- The plan file is always written when a migration SQL file is generated.
- The plan contains a machine-readable summary:

```json
{
  "migration_id": "primary__0001_add_users",
  "operations": [
    {
      "type": "add_column",
      "table": "users",
      "column": "age",
      "severity": "INFO"
    }
  ],
  "required_flags": [],
  "checksum": "sha256..."
}
```

- `migration_id` should align with the generated migration artifact.
- `operations` should be derived from DBWarden's internal change representation.
- `checksum` should cover the upgrade SQL content that DBWarden will execute.
- `migration_table` is configurable in `database_config(...)`.
- Only the migration tracking table is configurable in this branch.
- Lock and future seed tables remain fixed unless a later branch adds separate settings.

Example config:

```python
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="clickhouse",
    database_url="clickhouse://default@localhost:8123/default",
    migration_table="custom_migrations",
)
```

Implementation notes:
- All hardcoded `dbwarden_migrations` references must route through config-aware query generation.
- Keep branch 1 limited to migration plan metadata and migration table configurability.

### Branch 2: `feature/core-sandbox-and-dry-run`

Scope:
- Add `migrate --dry-run --sandbox`.
- Start a temporary database container and apply pending migrations there.
- ClickHouse is the first supported sandbox backend.
- Design the sandbox layer so additional providers can be added later.

Supported backends in scope:
- ClickHouse
- PostgreSQL
- MySQL
- SQLite

Requirements:
- Requires Docker.
- Must not modify the target database.
- Reports success or failure clearly.

### Branch 3: `feature/core-seeds`

Scope:
- Add versioned seed management separate from migrations.
- Add commands: `seed create`, `seed apply`, `seed list`, `seed rollback`.

Requirements:
- Seed files live in `seeds/` by default.
- Naming pattern: `V{version}__description.sql` or `V{version}__description.py`.
- Applied seeds are tracked in a fixed `_dbwarden_seeds` table.
- Seeds are idempotent and are not re-applied after being recorded.
- Python seeds support both raw connections and SQLAlchemy sessions.

Python seed contract:
- Provide access to both a raw connection and a SQLAlchemy session.
- Users can choose which one to use via the function argument contract or execution context.

### Branch 4: `feature/clickhouse-table-features`

Scope:
- Full ClickHouse table engine support.
- `ORDER BY`, `PRIMARY KEY`, `PARTITION BY`, `SAMPLE BY`.
- TTL expressions.
- Per-column codecs.
- Specialized ClickHouse types.

Model metadata examples:

```python
__table_args__ = {
    "clickhouse_engine": ("ReplacingMergeTree", "version_column"),
    "clickhouse_order_by": ["region", "event_time"],
    "clickhouse_primary_key": "region",
    "clickhouse_partition_by": "toYYYYMM(event_time)",
    "clickhouse_sample_by": "intHash64(user_id)",
    "clickhouse_ttl": [
        "event_time + INTERVAL 1 MONTH DELETE",
        "event_time + INTERVAL 1 YEAR TO DISK 'cold'",
    ],
}
```

Column codec example:

```python
Column("data", String, info={"clickhouse_codec": "ZSTD(3)"})
```

### Branch 5: `feature/clickhouse-objects-and-safety`

Scope:
- Materialized views.
- Projections.
- External dictionaries.
- Safety analyser.
- `check` command.

Safety analyser levels:
- `INFO`: safe automatic changes.
- `WARNING`: allowed only with `--force`.
- `ERROR`: blocked and accompanied by remediation guidance.

Materialized view notes:
- `clickhouse_mv_populate` exists and defaults to `False`.
- DBWarden should warn if `clickhouse_mv_populate=True`.

Replicated engine notes:
- Support `clickhouse_zookeeper_path` and `clickhouse_replica_name` in `__table_args__`.

### Branch 6: `feature/fastapi-runtime-expansion`

Scope:
- Expand `DBWardenHealthRouter`.
- Add a distributed Redis-backed migration lock helper.
- Add request-scoped DB/session dependency support.

Issues covered in this branch:
- `#20` feat(fastapi): add `get_session` `AsyncSession` dependency from DBWarden config
- `#21` feat(fastapi): add `DBWardenHealthRouter` for runtime DB/migration health endpoints
- `#8` feat(fastapi): add `check_schema_on_startup` helper
- `#9` feat(fastapi): add `migration_context` lifespan context manager

Endpoints:
- `GET /dbwarden/health`
- `GET /dbwarden/status`
- `POST /dbwarden/migrate` guarded by API key when enabled

Runtime helpers:
- `migration_lock(redis_client, key="dbwarden_migrate", ttl=60)`
- request-level dependency that yields a ClickHouse connection or SQLAlchemy session

#### Issue `#20`: `get_session` dependency from DBWarden config

Purpose:
- Provide a FastAPI-native `AsyncSession` dependency that resolves entirely from the DBWarden config registry.
- Avoid manual engine, sessionmaker, or connection-string setup in application code.

Public API:

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dbwarden.fastapi import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session())]
AnalyticsSessionDep = Annotated[AsyncSession, Depends(get_session("analytics"))]
```

Requirements:
- Use Pydantic/FastAPI-style `Annotated` dependencies in the documented and recommended usage.
- `get_session()` yields the default database session.
- `get_session("analytics")` yields the named database session.
- Return type remains `AsyncSession`.
- Engine and session factory creation are lazy and cached per process.
- Sessions are request-scoped.
- Dev mode should transparently resolve `dev_database_url` when enabled.
- Route exceptions should trigger a session rollback before re-raising.
- Add an engine teardown helper:

```python
from dbwarden.fastapi import dispose_engines
```

Acceptance criteria:
- `Annotated[AsyncSession, Depends(get_session())]` works as the primary documented pattern.
- Multi-database usage works with `Annotated[AsyncSession, Depends(get_session("name"))]`.
- Rollback-on-error behavior is enforced.
- Cached async engines can be disposed cleanly at shutdown.

#### Issue `#21`: runtime health router

Purpose:
- Provide a mountable FastAPI `APIRouter` that exposes runtime database health and migration state.

Public API:

```python
from dbwarden.fastapi import DBWardenHealthRouter

app.include_router(DBWardenHealthRouter(), prefix="/health")
```

Endpoints:
- `GET /health/` for overall health across all configured databases
- `GET /health/{database_name}` for one configured database

Status behavior:
- `healthy` or equivalent success state when all databases are reachable and have zero pending migrations
- `degraded` when databases are reachable but one or more have pending migrations
- `unreachable` or equivalent error state when any database cannot be connected to
- HTTP `200` for healthy or degraded responses
- HTTP `503` when any database is unreachable
- HTTP `404` for unknown database names

Implementation notes:
- Share underlying runtime health logic with startup checks.
- Include connectivity and migration-state details in the response.
- The router should be mountable with one import and one `include_router(...)` call.

Acceptance criteria:
- Router serves both overall and per-database endpoints.
- Status code behavior matches the runtime health contract.
- Unknown databases return `404`.

#### Issue `#8`: `check_schema_on_startup`

Purpose:
- Provide a read-only startup helper for schema and connectivity validation.

Public API:

```python
from dbwarden.fastapi import check_schema_on_startup
```

Requirements:
- Validate database connectivity and migration/schema state.
- Support strict startup failure and warning-only behavior.
- Must not mutate schema or data.
- Be safe for production startup paths.
- Produce clear diagnostics when schema is incompatible or migrations are pending.

Acceptance criteria:
- Works from FastAPI startup/lifespan code.
- Fails startup when strict mode is enabled and validation fails.
- Can be used as a read-only production gate.

#### Issue `#9`: `migration_context`

Purpose:
- Standardize FastAPI lifespan startup migration and startup-check behavior behind one context manager.

Public API:

```python
from dbwarden.fastapi import migration_context
```

Requirements:
- Support `mode="migrate"` and `mode="check"`.
- Forward configuration options to the startup helpers.
- Emit standardized logs including mode, duration, outcome, and database scope.
- Simplify FastAPI lifespan wiring compared to manual helper calls.

Acceptance criteria:
- Works cleanly inside FastAPI lifespan.
- Standardizes startup behavior and logging.

### Branch 7: `feature/observability`

Scope:
- Prometheus metrics.
- Structured JSON logging.

Metrics:
- `dbwarden_migrations_total{version, success}`
- `dbwarden_schema_version`
- `dbwarden_seed_version`
- `dbwarden_migration_duration_seconds`

Logging:
- Enable JSON logging with `DBWARDEN_LOG_JSON=true`.

### Branch 8: `feature/cli-enhancements`

Scope:
- `check`
- `downgrade --to=<version>`
- `make-rollback <migration_file>`
- `snapshot <table>`
- finish CLI wiring for features introduced by earlier branches

Notes:
- `check` depends on the safety analyser from branch 5.
- seed subcommands depend on branch 3.

### Branch 9: `feature/generate-models`

Scope:
- Add reverse engineering from a live database to SQLAlchemy model code.

Command:

```bash
dbwarden generate-models --output ./models/
```

Options:
- `--tables`
- `--exclude-tables`
- `--clickhouse-engines`
- `--relationships`
- `--dialect`
- `--single-file`

Output rules:
- Default output is one file per table.
- `--single-file` generates `models.py`.
- If `dbwarden.py` does not exist, DBWarden may generate it.

Use cases:
- bootstrapping from an existing database
- documenting an existing schema
- recovering models when migration scripts are missing

Warnings:
- Generated code is a starting point and may require manual cleanup.
- ClickHouse engine metadata may be incomplete and should surface warnings when best-effort guesses are used.

### Agreed Decisions

1. Only the migration tracking table is configurable in branch 1.
2. Migration plan files are always written when migrations are generated.
3. Python seeds will support both raw connections and SQLAlchemy sessions.
4. Model generation supports both one-file-per-table and `--single-file`; default is one file per table.
