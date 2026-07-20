---
seo:
  title: Declaring Metadata - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata
  robots: index,follow
  og:
    type: website
    title: Declaring Metadata - DBWarden Documentation
    description: 'PostgreSQL metadata is declared in a class Meta inner class on the
      model. This is the only supported surface: mappedcolumninfo=... raises DBWardenConfigError.'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Declaring Metadata - DBWarden Documentation
    description: 'PostgreSQL metadata is declared in a class Meta inner class on the
      model. This is the only supported surface: mappedcolumninfo=... raises DBWardenConfigError.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'PostgreSQL metadata is declared in a class Meta inner class on the
    model. This is the only supported surface: mappedcolumninfo=... raises DBWardenConfigError.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Declaring Metadata - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata
    description: 'PostgreSQL metadata is declared in a class Meta inner class on the
      model. This is the only supported surface: mappedcolumninfo=... raises DBWardenConfigError.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
      logo: https://dbwarden.emiliano-go.com/assets/images/og-image.png
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Databases
      item: https://dbwarden.emiliano-go.com/databases
    - '@type': ListItem
      position: 2
      name: PostgreSQL
      item: https://dbwarden.emiliano-go.com/databases/postgresql
    - '@type': ListItem
      position: 3
      name: Declaring Metadata
      item: https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata
seo_html: "<title>Declaring Metadata - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"PostgreSQL metadata is declared in a class Meta inner class\
  \ on the model. This is the only supported surface: mappedcolumninfo=... raises\
  \ DBWardenConfigError.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Declaring Metadata - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"PostgreSQL metadata\
  \ is declared in a class Meta inner class on the model. This is the only supported\
  \ surface: mappedcolumninfo=... raises DBWardenConfigError.\">\n<meta property=\"\
  og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Declaring Metadata - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"PostgreSQL metadata is declared\
  \ in a class Meta inner class on the model. This is the only supported surface:\
  \ mappedcolumninfo=... raises DBWardenConfigError.\">\n<meta name=\"twitter:image\"\
  \ content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta\
  \ name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Declaring Metadata - DBWarden Documentation\",\n    \"url\":\
  \ \"https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata\",\n\
  \    \"description\": \"PostgreSQL metadata is declared in a class Meta inner class\
  \ on the model. This is the only supported surface: mappedcolumninfo=... raises\
  \ DBWardenConfigError.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Declaring Metadata\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/declaring-metadata\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Declaring Metadata

PostgreSQL metadata is declared in a `class Meta` inner class on the model. This is the **only** supported surface: `mapped_column(info=...)` raises `DBWardenConfigError`.

## Table-Level Meta

Inherit from `PGTableMeta` on your `class Meta`:

```python
from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.databases.pgsql import PGTableMeta

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    class Meta(PGTableMeta):
        pg_fillfactor = 80
        pg_tablespace = "fastspace"
        pg_storage_params = {
            "fillfactor": 80,
            "autovacuum_enabled": "false",
        }
        pg_inherits = "base_entity"
        pg_excludes = [
            {"name": "excl_room_booking", "expression": "USING gist (room_id WITH =, during WITH &&)"},
        ]
```

`PGTableMeta` inherits from `TableMeta`, which provides common attributes shared across all backends:

| Attribute | Type | SQL |
|-----------|------|-----|
| `comment` | `str` | `COMMENT ON TABLE t IS '...'` |
| `indexes` | `list[IndexSpec]` | `CREATE INDEX ...` |
| `checks` | `list[CheckSpec]` | `ALTER TABLE t ADD CONSTRAINT ... CHECK (...)` |
| `uniques` | `list[UniqueSpec]` | `ALTER TABLE t ADD CONSTRAINT ... UNIQUE (...)` |

PostgreSQL-specific `PGTableMeta` attributes:

| Attribute | Type | SQL |
|-----------|------|-----|
| `pg_fillfactor` | `int` | `ALTER TABLE t SET (fillfactor = N)` |
| `pg_tablespace` | `str` | `ALTER TABLE t SET TABLESPACE name` |
| `pg_storage_params` | `dict[str, Any]` | `ALTER TABLE t SET (param = value)` |
| `pg_unlogged` | `bool` | `CREATE UNLOGGED TABLE ...` / `ALTER TABLE t SET UNLOGGED` |
| `pg_partition` | `dict` | `PARTITION BY RANGE / LIST / HASH (columns)` |
| `pg_inherits` | `str \| list[str]` | `ALTER TABLE t INHERIT parent` |
| `pg_excludes` | `list[ExcludeSpec]` | `ALTER TABLE t ADD CONSTRAINT ... EXCLUDE USING ...` |
| `pg_indexes` | `list[PgIndexSpec]` | `CREATE INDEX ...` (with `USING`, `WHERE`, `INCLUDE`, `NULLS NOT DISTINCT`, column sorting) |
| `pg_checks` | `list[CheckSpec]` | `ALTER TABLE t ADD CONSTRAINT ... CHECK (...)` (with `NO INHERIT`) |
| `pg_uniques` | `list[UniqueSpec]` | `ALTER TABLE t ADD CONSTRAINT ... UNIQUE (...)` (with `DEFERRABLE`, `NULLS NOT DISTINCT`, `INCLUDE`) |

Pythonic model definitions use the typed spec classes with full IDE autocomplete:

```python
from dbwarden.databases import IndexSpec, CheckSpec, UniqueSpec
from dbwarden.databases.pgsql import PgIndexSpec, ExcludeSpec

class Meta(PGTableMeta):
    indexes = [
        IndexSpec(name="ix_users_email", columns=["email"], unique=True),
    ]
    checks = [
        CheckSpec(name="ck_users_age", expression="age >= 0"),
    ]
    uniques = [
        UniqueSpec(name="uq_users_email", columns=["email"],
                   deferrable=True, initially_deferred=True),
    ]
    pg_excludes = [
        ExcludeSpec(name="excl_room_booking",
                    elements=[{"column": "room_id", "with": "="},
                              {"column": "during", "with": "&&"}]),
    ]
```

Plain dicts are also accepted for backwards compatibility, but typed specs are the recommended and idiomatic form.

### INHERITS

`pg_inherits` accepts a single parent or a list for multiple inheritance:

```python
# Single inheritance
pg_inherits = "base_entity"

# Multiple inheritance
pg_inherits = ["base_entity", "audit_mixin"]
```

### ON COMMIT (Temporary Tables)

For `pg_unlogged` tables or temporary tables, use `ON COMMIT` options via `pg_on_commit`:

| Value | Behaviour |
|-------|-----------|
| `PRESERVE ROWS` | Default: rows persist across transaction boundaries |
| `DELETE ROWS` | All rows deleted at transaction end |
| `DROP` | Table dropped at transaction end |

### WITH OPTIONS (Storage Parameters)

Beyond `pg_fillfactor`, additional storage parameters can be set:

```sql
ALTER TABLE users SET (autovacuum_vacuum_threshold = 100, toast_tuple_target = 1024);
```

See [Storage Parameters](storage-params.md) for the complete list.

## JSONB Columns

JSONB columns use `from sqlalchemy.dialects.postgresql import JSONB`:

```python
from sqlalchemy.dialects.postgresql import JSONB

class User(Base):
    __tablename__ = "users"
    metadata = Column(JSONB)

    class Meta(PGTableMeta):
        pg_indexes = [
            PgIndexSpec("ix_users_metadata", ["metadata"], using="gin"),
        ]
```

For smaller indexes on path-based queries, use the `jsonb_path_ops` operator class:

```python
PgIndexSpec("ix_users_metadata", ["metadata"],
    using="gin",
    postgresql_ops={"metadata": "jsonb_path_ops"})
```

JSONB column type changes (e.g., `json` -> `jsonb`) are classified as **SAFE**.

### JSONB Operators for Indexing

GIN indexes on JSONB columns support these default operators:

| Operator | Description |
|----------|-------------|
| `?` | Does the string exist as a top-level key? |
| `?\|` | Do any of these strings exist as keys? |
| `?&` | Do all of these strings exist as keys? |
| `@>` | Does the left JSON contain the right JSON path/value? |
| `<@` | Is the left JSON contained by the right JSON? |

With `jsonb_path_ops`, only `@>` and `<@` are supported, but the index is smaller and faster for path queries.

## Column-Level Meta

Use `PGColumnMeta` inner classes for per-column metadata:

```python
from dbwarden.databases.pgsql import PGTableMeta, PGColumnMeta, pg

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    bio: Mapped[str] = mapped_column(Text)

    class Meta(PGTableMeta):
        class id(PGColumnMeta):
            pg = pg.field(identity="always", identity_start=100, identity_increment=1)

        class bio(PGColumnMeta):
            pg = pg.field(storage="EXTENDED", compression="pglz", collation="en_US.UTF-8")
```

`PGColumnMeta` common attributes:

| Attribute | Type | SQL |
|-----------|------|-----|
| `comment` | `str` | `COMMENT ON COLUMN t.c IS '...'` |
| `public` | `bool` | Controls field visibility |
| `pg` | `PgFieldSpec` | PostgreSQL-specific column options |

PostgreSQL-specific `PgFieldSpec` fields (set via `pg.field(...)`):

| Keyword | Type | SQL |
|---------|------|-----|
| `collation` | `str` | `ALTER COLUMN c TYPE t COLLATE "name"` |
| `storage` | `str` | `ALTER COLUMN c SET STORAGE {PLAIN\|MAIN\|EXTERNAL\|EXTENDED}` |
| `compression` | `str` | `ALTER COLUMN c SET COMPRESSION {pglz\|zstd}` (PG 14+) |
| `generated` | `str` | `GENERATED ALWAYS AS (expr) STORED` |
| `identity` | `str` | `ADD GENERATED {ALWAYS\|BY DEFAULT} AS IDENTITY` |
| `identity_start` | `int` | Sequence `START WITH` |
| `identity_increment` | `int` | Sequence `INCREMENT BY` |
| `identity_min` | `int` | Sequence `MINVALUE` |
| `identity_max` | `int` | Sequence `MAXVALUE` |

### Column Defaults

Column default values are set via SQLAlchemy's `server_default` parameter, not through `PGColumnMeta`. The default is emitted as `ALTER COLUMN c SET DEFAULT expr` in DDL:

```python
from sqlalchemy import text

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("NOW()"))
    slug: Mapped[str] = mapped_column(String, server_default=text("gen_random_uuid()"))
```

`server_default=text("...")` renders the SQL expression directly. Use `server_default="constant"` (string) for literal defaults.

## Foreign Key Options

FK options are captured from the database by `generate-models` and emitted in the `ForeignKey` constructor:

```python
from sqlalchemy import ForeignKey

class OrderItem(Base):
    __tablename__ = "order_items"
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE", onupdate="CASCADE", deferrable=True),
        nullable=False,
    )
```

Supported FK options: `ondelete`, `onupdate`, `deferrable`, `initially`, `match` (`FULL`/`PARTIAL`/`SIMPLE`).

See [Constraints](constraints.md) for FK lifecycle and deferrable behaviour.
