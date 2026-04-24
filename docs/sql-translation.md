# SQL Translation

DBWarden includes a SQL translation layer to support development workflows where your primary database differs from your development database.

The most common case is:

- Primary database: PostgreSQL/MySQL/MariaDB/ClickHouse
- Development database: SQLite (`--dev` mode)

This keeps local development fast while still allowing production-targeted schemas.

## Why SQL Translation Exists

SQLite does not support all backend-specific SQL types and default expressions used by other databases.

Without translation, generated migrations can fail in local development when they contain backend-specific types like `UUID`, `JSONB`, or default expressions like `now()`.

DBWarden translation solves this by adapting generated SQL for SQLite compatibility.

## When translation is active

Translation is applied when all are true:

- command runs with `--dev`
- selected database resolves to a SQLite `dev_database_url`
- command path generates SQL from models (`make-migrations`)

It is not a runtime SQL proxy for arbitrary manual SQL.

## How It Works

When you run commands in development mode and target a SQLite dev database:

```bash
dbwarden --dev make-migrations "sync models" -d primary
```

DBWarden uses this flow:

1. Loads the selected database config and resolves `dev_database_url`.
2. Detects that the active target backend is SQLite.
3. Extracts model metadata from SQLAlchemy models.
4. Translates backend-specific types/defaults to SQLite-compatible SQL.
5. Generates migration SQL with translated definitions.

Translation is applied during migration generation, not as a post-processing regex pass.

## Type conversion behavior

Common conversions:

| Source type | SQLite output |
|-------------|---------------|
| `UUID` | `TEXT` |
| `JSON` / `JSONB` | `TEXT` |
| `TIMESTAMPTZ` | `DATETIME` |
| `SERIAL` / `BIGSERIAL` | `INTEGER` |
| ClickHouse nullable numeric forms | `INTEGER`/`REAL` depending on source |

If a type cannot be translated safely:

- non-strict mode: fallback to `TEXT` + warning
- strict mode: fail migration generation

## Type Translation Behavior

DBWarden maps many backend-specific types to SQLite-compatible types.

Examples:

- `UUID` -> `TEXT`
- `JSON` / `JSONB` -> `TEXT`
- `TIMESTAMPTZ` -> `DATETIME`
- `SERIAL` / `BIGSERIAL` -> `INTEGER`
- `Nullable(UInt64)` (ClickHouse) -> `INTEGER`

For unsupported or unknown types that cannot be converted safely:

- DBWarden falls back to `TEXT`
- Logs a warning indicating the fallback

## Default expression handling

Backend expressions such as `now()` or `gen_random_uuid()` may not have direct SQLite equivalents.

In non-strict mode, unsupported defaults are dropped with warning.

In strict mode, unsupported defaults fail generation.

## Default Expression Translation

DBWarden also handles unsupported default expressions.

Examples of expressions that may be removed for SQLite compatibility:

- `now()`
- `gen_random_uuid()`
- sequence-based defaults (like `nextval(...)`)

In non-strict mode, unsupported defaults are removed and a warning is logged.

## Strict Translation Mode

If you want hard failures instead of fallback behavior:

```bash
dbwarden --dev --strict-translation make-migrations "sync models" -d primary
```

In strict mode:

- Unknown/unsupported type conversions raise errors
- Unsupported default expression conversions raise errors

Use this when you want to catch every lossy conversion early.

## Recommended team workflow

1. iterate quickly with `--dev` (SQLite)
2. keep strict checks in CI (`--strict-translation`)
3. validate release candidate migrations against production-like database

This balances speed and correctness.

## Recommended Setup

For fast local testing and predictable developer workflows, use SQLite as your dev database:

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

Then run development commands with:

```bash
dbwarden --dev migrate -d primary
dbwarden --dev make-migrations "add indexes" -d primary
```

## Troubleshooting

`--dev mode is enabled, but database '<name>' has no dev_database_url configured`:

- add `dev_database_url` for that database entry

Unexpected type fallback to `TEXT`:

- inspect model type for backend-specific declaration
- re-run with `--strict-translation` to fail fast and fix explicitly

Generated SQL differs from production expectations:

- expected in SQLite compatibility mode; validate final release migrations on production-like backend

## Notes and Limitations

- Translation focuses on compatibility for local development.
- Some backend features cannot be represented exactly in SQLite.
- For production accuracy, always test migrations against your production-like database too.

## Navigation

- Previous: [Migration File Format](migration-files.md)
- Next: [Migration Locking](advanced/migration-locking.md)
