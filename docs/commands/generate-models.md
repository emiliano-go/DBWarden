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

## PostgreSQL First-Class Output

For PostgreSQL databases, `generate-models` reverse-engineers all supported metadata and emits it as `class Meta` inner classes with `PGTableMeta` and `PGColumnMeta`:

```python
from dbwarden import Base, PGTableMeta, PGColumnMeta

class User(Base):
    __tablename__ = "users"

    id:    Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio:   Mapped[str | None] = mapped_column(Text, nullable=True)

    class Meta(PGTableMeta):
        comment = "Core user accounts"
        pg_fillfactor = 80

        class id(PGColumnMeta):
            pg_identity = "always"
            pg_identity_start = 100
            pg_identity_increment = 1

        class bio(PGColumnMeta):
            pg_storage = "EXTENDED"
            pg_collation = "en_US.UTF-8"
```

The following metadata is reverse-engineered:

- **Identity columns**: `GENERATED ALWAYS/BY DEFAULT AS IDENTITY` with sequence options
- **Collation**: per-column `COLLATE` setting
- **Storage**: per-column `STORAGE` (PLAIN, MAIN, EXTERNAL, EXTENDED)
- **Generated columns**: `GENERATED ALWAYS AS (...) STORED`
- **Table fillfactor**: `WITH (fillfactor = N)`
- **Tablespace**: `SET TABLESPACE`
- **Inheritance**: `INHERITS (parent)`
- **EXCLUDE constraints**: `EXCLUDE USING ...`
- **FK options**: `ondelete`, `onupdate`, `deferrable` on `ForeignKey()`
- **Index options**: `USING`, `WHERE`, `INCLUDE`, `WITH`, `TABLESPACE`, `NULLS NOT DISTINCT`
- **Table and column comments**

For the complete feature reference, see [PostgreSQL Deep Dive](../databases/postgresql.md).

## Use cases

- **Bootstrapping**: start a new project from an existing database
- **Documentation**: generate model stubs to document the schema
- **Recovery**: regenerate models when migration scripts are missing

## Warnings

- Generated code requires manual review and cleanup
- ClickHouse engine metadata may be incomplete without `--clickhouse-engines`
