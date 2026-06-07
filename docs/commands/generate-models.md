# `generate-models`

Reverse-engineer SQLAlchemy model code from a live database.

## Usage

```bash
dbwarden generate-models --output ./models/ --database primary
dbwarden generate-models --output ./models/ --database primary --single-file
dbwarden generate-models --database primary --tables users,posts
dbwarden generate-models --database primary --exclude-tables logs,audit
```

## Options

| Option | Description |
|--------|-------------|
| `--output`, `-o` | Output directory (default: `models`) |
| `--tables` | Comma-separated list of tables to include |
| `--exclude-tables` | Comma-separated list of tables to exclude |
| `--clickhouse-engines` | Include ClickHouse engine metadata in `__table_args__` |
| `--relationships` | Generate `relationship()` attributes for foreign keys |
| `--dialect` | SQL dialect for type mapping (auto-detected from database type) |
| `--single-file` | Generate a single `models.py` instead of one file per table |
| `--database`, `-d` | Target database name |

## Output rules

- **Default**: one `.py` file per table (e.g., `users.py`, `posts.py`)
- **`--single-file`**: generates `models.py` with all models
- Each file imports `declarative_base()` and defines `Base`

## Type mapping

Database column types are mapped to SQLAlchemy types:

| Database Type | SQLAlchemy Type |
|---------------|----------------|
| `INTEGER` | `Integer` |
| `VARCHAR(N)` | `String(length=N)` |
| `TEXT` | `Text` |
| `BOOLEAN` / `TINYINT(1)` | `Boolean` |
| `DECIMAL(P,S)` | `Numeric(precision=P, scale=S)` |
| `DATETIME` / `TIMESTAMP` | `DateTime` |
| `BIGINT` | `BigInteger` |
| `FLOAT` / `DOUBLE` | `Float` |
| `Nullable(...)` (ClickHouse) | Inner type (nullable is explicit) |

## Use cases

- **Bootstrapping**: start a new project from an existing database
- **Documentation**: generate model stubs to document the schema
- **Recovery**: regenerate models when migration scripts are missing

## Warnings

- Generated code requires manual review and cleanup
- ClickHouse engine metadata may be incomplete without `--clickhouse-engines`
