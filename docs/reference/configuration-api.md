# Configuration API

`database_config(...)` defines a database entry in your Python config source.

## Function signature

```python
def database_config(
    database_name: str,
    database_type: Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"],
    database_url: str,
    default: bool = False,
    migrations_dir: str | None = None,
    model_paths: list[str] | None = None,
    dev_database_type: str | None = None,
    dev_database_url: str | None = None,
    overlap_models: bool = False,
    secure_values: bool = False,
) -> None:
    """Register a database in DBWarden."""
```

## Required arguments

| Argument | Type | Description |
|----------|------|-------------|
| `database_name` | `str` | unique name for this database in your project |
| `database_type` | `str` | backend type: `sqlite`, `postgresql`, `mysql`, `mariadb`, or `clickhouse` |
| `database_url` | `str` | connection URL for this database |

## Optional arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `default` | `bool` | `False` | if `True`, this database is used when `--database` is omitted |
| `migrations_dir` | `str | None` | `None` | custom migration directory path (defaults to `migrations/<database_name>`) |
| `model_paths` | `list[str] | None` | `None` | list of Python import paths containing SQLAlchemy models for this database |
| `dev_database_type` | `str | None` | `None` | backend type for local development (used with `--dev`) |
| `dev_database_url` | `str | None` | `None` | connection URL for local development (used with `--dev`) |
| `overlap_models` | `bool` | `False` | if `True`, allow model path overlap with other databases |
| `secure_values` | `bool` | `False` | if `True`, display commands show variable names instead of resolved values |

## Field descriptions

### `database_name`

A unique identifier for this database within your project.

- Must be unique across all entries in your config source
- Used in CLI `--database` / `-d` flags to select this database
- Becomes part of migration filename prefix (for versioned migrations)

Examples: `"primary"`, `"analytics"`, `"legacy"`

### `database_type`

The database backend technology. Each value determines:

- URL parsing behavior
- SQL dialect and syntax handling
- Available features (transactions, DDL, constraints)

Valid values: `sqlite`, `postgresql`, `mysql`, `mariadb`, `clickhouse`

### `database_url`

A connection URL string in the format:

```
[dialect+driver://user:password@]host[:port][/database][?options]
```

Examples:

```python
# PostgreSQL
database_url = "postgresql://user:password@localhost:5432/mydb"

# SQLite (relative path)
database_url = "sqlite:///./development.db"

# SQLite (absolute path)
database_url = "sqlite:////absolute/path/to/database.db"

# MySQL
database_url = "mysql://user:password@localhost:3306/mydb"

# ClickHouse
database_url = "http://user:password@clickhouse-host:8123/mydb"
```

### `default`

When `True`, this database is selected when `--database` / `-d` is not specified.

**Rule:** Exactly one entry must have `default=True`.

### `migrations_dir`

Path where this database's migration files are stored.

- Defaults to `migrations/<database_name>`
- Each database should have its own directory to avoid collision
- Versioned migration files go here (`NNNN_description.sql`)
- Repeatable migration files go here (`RA__*.sql`, `ROC__*.sql`)

### `model_paths`

A list of Python import paths where DBWarden should discover SQLAlchemy model definitions.

**When required:** When more than one database is configured, each entry needs explicit `model_paths` to keep model discovery boundaries clear.

**How it works:** DBWarden imports each path and inspects classes inheriting from `DeclarativeBase` or `declarative_base()`.

### `dev_database_type` and `dev_database_url`

These define an alternate connection for local development workflows.

When `--dev` is passed to any DBWarden command:

- `database_type` is swapped to `dev_database_type`
- `database_url` is swapped to `dev_database_url`

This lets you:

- Use SQLite locally for speed (if production is PostgreSQL)
- Target a separate development database instance
- Test migrations safely before running against production-like databases

**Recommendation:** Use SQLite with `dev_database_url = "sqlite:///./development.db"` for the fastest local iteration loop.

### `overlap_models`

By default, DBWarden prevents model path overlap between databases.

Set `overlap_models=True` when:

- Two databases legitimately share model definitions
- You understand the behavior implications (both databases will include overlapping tables)

### `secure_values`

When enabled, CLI display commands show the original variable/expression for non-literal arguments instead of resolved values.

Use this when:

- Your config uses environment variables or expressions for secrets
- You want terminal output to avoid exposing credentials

Example:

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url=DATABASE_URL,
    secure_values=True,
)
```

With `secure_values=True`, `dbwarden settings show` will display `DATABASE_URL` instead of the resolved connection string.

## Configuration rules (enforced at load time)

DBWarden validates your config to prevent dangerous misconfigurations:

| Rule | Error message (if violated) |
|------|---------------------------|
| Exactly one `default=True` | `Exactly one default=True required` |
| Unique `database_name` across all entries | `Duplicate database_name` |
| Unique `database_url` across all entries | `Duplicate database_url` |
| Unique physical target (even across credentials) | `Duplicate database target detected` |
| Required `model_paths` when multiple databases | `model_paths is required when more than one database is configured` |
| Explicit `overlap_models` when paths overlap | `model_paths overlap detected` |
| If `dev_database_type` set, `dev_database_url` also required | `dev_database_url is required when dev_database_type is set` |

## Loading and resolution

Config is loaded by importing your Python config source and executing `database_config(...)` calls.

The resolution priority is:

1. Look for `dbwarden.py` in the current directory or parent directories
2. Full scan for any file containing `database_config(...)` calls
3. If `DBWARDEN_CONFIG_MODULE` environment variable is set, use that module

If more than one discovery source is found, DBWarden fails with an ambiguity error.

## Examples

### Minimal single-database setup

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/mydb",
)
```

### With local development (recommended)

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/mydb",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

### Multi-database setup

```python
from dbwarden import database_config


database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    model_paths=["app/models/api"],
)

database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url="http://clickhouse:password@clickhouse-host:8123/analytics",
    model_paths=["app/models/analytics"],
)
```

## Navigation

- Previous: [Supported Databases](../databases.md)
- Next: [Architecture](../architecture-deep-dive.md)