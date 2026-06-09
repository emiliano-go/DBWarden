---
seo:
  title: 2. Defining Models and Generating Migrations - DBWarden Documentation
  description: 2. Defining Models and Generating Migrations What You'll Learn How
    to define SQLAlchemy models with class Meta annotations How makemigrations generates
    SQL from model changes How the generated SQL...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/02-models-and-migrations/
  robots: index,follow
  og:
    type: website
    title: 2. Defining Models and Generating Migrations - DBWarden Documentation
    description: 2. Defining Models and Generating Migrations What You'll Learn How
      to define SQLAlchemy models with class Meta annotations How makemigrations generates
      SQL from model changes How the generated SQL...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/02-models-and-migrations/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: 2. Defining Models and Generating Migrations - DBWarden Documentation
    description: 2. Defining Models and Generating Migrations What You'll Learn How
      to define SQLAlchemy models with class Meta annotations How makemigrations generates
      SQL from model changes How the generated SQL...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: 2. Defining Models and Generating Migrations - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/cookbook/02-models-and-migrations/
    description: 2. Defining Models and Generating Migrations What You'll Learn How
      to define SQLAlchemy models with class Meta annotations How makemigrations generates
      SQL from model changes How the generated SQL...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# 2. Defining Models and Generating Migrations

## What You'll Learn

- How to define SQLAlchemy models with `class Meta` annotations
- How `make-migrations` generates SQL from model changes
- How the generated SQL maps to database DDL
- How to create manual migrations with `dbwarden new`
- How to extract rollback SQL from an existing migration

## Prerequisites

- Completed [Section 1: Project Setup](01-project-setup.md)
- `examples/core/` with `app/models.py`

## Step 1: The Models

Our example project defines four models in `examples/core/app/models.py`. Here they are with explanations:

### User

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    class Meta(TableMeta):
        comment = "Core user accounts"
        indexes = [
            IndexSpec(name="ix_users_created_at", columns=["created_at"]),
        ]
```

Key points:

- `unique=True` on `email` and `username` generates `UNIQUE` constraints
- `nullable=True` (the default) allows `NULL`; `nullable=False` adds `NOT NULL`
- `server_default=text(...)` becomes a database-level `DEFAULT` clause in the DDL; `default=` is a Python-level default and is not rendered in SQL
- `class Meta(TableMeta)` is how we attach table-level metadata
- `IndexSpec` generates a named `CREATE INDEX` statement

### Post

```python
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    class Meta(TableMeta):
        comment = "User blog posts"
        indexes = [
            IndexSpec(name="ix_posts_user_id", columns=["user_id"]),
            IndexSpec(name="ix_posts_created_at", columns=["created_at"]),
        ]
```

Key points:

- `ForeignKey("users.id")` generates a `REFERENCES` clause
- Foreign key targets are rendered inline in `CREATE TABLE`

### Product (with CHECK constraint)

```python
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    in_stock = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    class Meta(TableMeta):
        comment = "Product catalog"
        checks = [
            {"name": "ck_products_price_positive", "sql": "price > 0"},
        ]
```

Key points:

- `checks` in `class Meta` generates `CHECK` constraints
- Each check needs a `name` (constraint name) and `sql` (the expression)
- This prevents negative prices at the database level

### Tag

```python
class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    class Meta(TableMeta):
        comment = "Taxonomy tags for products"
```

The simplest model — just an ID and a unique name.

## Step 2: Generating the Migration

```bash
cd examples/core
bash scripts/02-models-migrations.sh
```

The first script step runs:

```bash
dbwarden make-migrations "create core tables" --database primary
```

This compares the current model state against the database (or a stored snapshot). Since this is a fresh project, it detects four new tables and generates:

```sql
-- upgrade

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME
)

CREATE TABLE IF NOT EXISTS products (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price FLOAT NOT NULL,
    description TEXT,
    in_stock BOOLEAN DEFAULT TRUE,
    created_at DATETIME
)

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME
)

-- rollback

DROP TABLE users
DROP TABLE tags
DROP TABLE products
DROP TABLE posts
```

> **Note:** The example uses SQLite, which has limited DDL support. With PostgreSQL, DBWarden generates additional features:
> - **`CREATE INDEX IF NOT EXISTS ...`** — from `IndexSpec` entries in `class Meta`
> - **`COMMENT ON TABLE ...`** — from `Meta.comment` attributes
> - **`CONSTRAINT ... CHECK (...)`** — from `Meta.checks`
> - **`server_default`** expressions rendered as native SQL defaults
> - Inline `REFERENCES` become table-level `FOREIGN KEY` constraints
>
> The generated SQL is always backend-specific. DBWarden adapts to the `database_type` configured in `dbwarden.py`.

### Reading the Generated SQL

Let's walk through what each section does:

**`-- upgrade`** — Applied when you run `dbwarden migrate`

1. **`CREATE TABLE IF NOT EXISTS posts (...)`** — Creates posts with a foreign key reference to `users(id)` (inline `REFERENCES` style for SQLite). The foreign key originates from `ForeignKey("users.id")` on the `user_id` column.

2. **`CREATE TABLE IF NOT EXISTS products (...)`** — Creates products with a `CHECK` constraint defined in `class Meta`. In SQLite, CHECK constraints must be inline; with PostgreSQL they become `CONSTRAINT ... CHECK (...)`.

3. **`CREATE TABLE IF NOT EXISTS tags (...)`** — Simple table with a unique constraint on `name`.

4. **`CREATE TABLE IF NOT EXISTS users (...)`** — Creates the users table with all columns, primary key, and unique constraints inline.

Note that with this SQLite backend the table order differs from the order in our Python models, and some features are omitted:
- **IndexSpec entries** generate `CREATE INDEX` only on PostgreSQL and ClickHouse
- **`COMMENT ON TABLE`** is only generated for PostgreSQL
- **`server_default`** expressions render as native SQL defaults on PostgreSQL

**`-- rollback`** — Applied when you run `dbwarden rollback`

1. Drops tables. Order may vary by backend — DBWarden handles dependency ordering automatically.

### Auto-generated Migration Name

The migration file is named automatically:

```
primary__0001_create_core_tables.sql
```

The naming pattern is:

```
{database_name}__{4-digit-version}_{auto-generated-description}.sql
```

## Step 3: Creating a Manual Migration

Sometimes you need a migration that isn't model-driven — a data backfill, a stored procedure, or a complex SQL operation.

```bash
dbwarden new add_custom_table --database primary
```

This creates a blank migration:

```sql
-- upgrade

-- TODO: write your upgrade SQL here

-- rollback

-- TODO: write your rollback SQL here
```

You fill in both sections manually. Manual migrations follow the same file naming convention and are tracked alongside auto-generated ones.

## Step 4: Extracting Rollback SQL

If you have a migration file and need to extract just its rollback section:

```bash
dbwarden make-rollback migrations/primary/primary__0001_create_core_tables.sql
```

This prints the rollback SQL to stdout. Useful for quickly verifying what a rollback will do before running it.

## Key Takeaways

- DBWarden generates explicit, reviewable SQL — no hidden runtime behavior
- Every migration has both `-- upgrade` and `-- rollback` sections
- `class Meta(TableMeta)` is where table-level metadata (comments, indexes, checks) lives
- `IndexSpec` produces named `CREATE INDEX` statements — always prefer named indexes
- `dbwarden new` creates blank migrations for non-model-driven changes
- `dbwarden make-rollback` extracts rollback SQL for review

## Related Documentation

- [SQLAlchemy Models Reference](../models.md)
- [Modeling Guide](../tutorial/modeling.md)
- [Migration File Format](../migration-files.md)
- [`make-migrations` command](../commands/make-migrations.md)

## Next

[Section 3: Apply & Inspect](03-apply-and-inspect.md)
