---
seo:
  title: Tables & Columns - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns
  robots: index,follow
  og:
    type: website
    title: Tables & Columns - DBWarden Documentation
    description: 'Handlers: TableHandler, RenameTableHandler, ColumnHandler, PgTableHandler,
      StorageParamsHandler DIFF phase'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Tables & Columns - DBWarden Documentation
    description: 'Handlers: TableHandler, RenameTableHandler, ColumnHandler, PgTableHandler,
      StorageParamsHandler DIFF phase'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handlers: TableHandler, RenameTableHandler, ColumnHandler, PgTableHandler,
    StorageParamsHandler DIFF phase'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Tables & Columns - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns
    description: 'Handlers: TableHandler, RenameTableHandler, ColumnHandler, PgTableHandler,
      StorageParamsHandler DIFF phase'
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
      name: Tables And Columns
      item: https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns
seo_html: "<title>Tables &amp; Columns - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Handlers: TableHandler, RenameTableHandler, ColumnHandler,\
  \ PgTableHandler, StorageParamsHandler DIFF phase\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns\">\n<meta\
  \ name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Tables &amp; Columns - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Handlers: TableHandler,\
  \ RenameTableHandler, ColumnHandler, PgTableHandler, StorageParamsHandler DIFF phase\"\
  >\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Tables &amp; Columns - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Handlers: TableHandler, RenameTableHandler,\
  \ ColumnHandler, PgTableHandler, StorageParamsHandler DIFF phase\">\n<meta name=\"\
  twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Tables & Columns - DBWarden Documentation\",\n    \"url\": \"\
  https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns\",\n  \
  \  \"description\": \"Handlers: TableHandler, RenameTableHandler, ColumnHandler,\
  \ PgTableHandler, StorageParamsHandler DIFF phase\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Tables And Columns\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/tables-and-columns\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Tables & Columns

**Handlers**: `TableHandler`, `RenameTableHandler`, `ColumnHandler`, `PgTableHandler`, `StorageParamsHandler` (DIFF phase)

## Table Lifecycle

| Operation | DDL |
|-----------|-----|
| Create table | `CREATE TABLE name (...)` |
| Drop table | `DROP TABLE IF EXISTS name CASCADE;` |
| Rename table | `ALTER TABLE old_name RENAME TO new_name;` |
| Alter table comment | `COMMENT ON TABLE name IS 'comment';` |

## Column Lifecycle

| Operation | DDL |
|-----------|-----|
| Add column | `ALTER TABLE t ADD COLUMN c type;` |
| Drop column | `ALTER TABLE t DROP COLUMN c;` |
| Change type | `ALTER TABLE t ALTER COLUMN c TYPE newtype;` |
| Change nullable | `ALTER TABLE t ALTER COLUMN c SET/DROP NOT NULL;` |
| Change default | `ALTER TABLE t ALTER COLUMN c SET/DROP DEFAULT;` |
| Change comment | `COMMENT ON COLUMN t.c IS 'comment';` |
| Change autoincrement | `CREATE/DROP SEQUENCE` + `SET/DROP DEFAULT nextval` |
| Change PG meta | `SET STORAGE`, `SET COMPRESSION`, `SET COLLATION`, identity options |
| Rename column | `ALTER TABLE t RENAME COLUMN c TO new_name;` |

## Table Properties

| Property | Meta Attribute | DDL |
|----------|---------------|-----|
| Fillfactor | `pg_fillfactor` | `ALTER TABLE t SET (fillfactor = N);` |
| Tablespace | `pg_tablespace` | `ALTER TABLE t SET TABLESPACE name;` |
| Unlogged | `pg_unlogged` | `CREATE UNLOGGED TABLE` / `ALTER TABLE t SET UNLOGGED;` |
| Inheritance | `pg_inherits` | `ALTER TABLE t INHERIT parent;` |
| Storage params | (via handler) | `ALTER TABLE t SET (param = value);` |
| ON COMMIT | `pg_on_commit` | `ON COMMIT DELETE ROWS` / `DROP` / `PRESERVE ROWS` |

### Storage Params

`pg_storage_params` stores raw PostgreSQL table storage options. `pg_fillfactor` is kept as a shorthand and is folded into `pg_storage_params["fillfactor"]` during discovery.

```python
class Meta(PGTableMeta):
    pg_storage_params = {
        "fillfactor": 80,
        "autovacuum_enabled": "false",
    }
```

Generated DDL:

```sql
ALTER TABLE users SET (fillfactor = 80, autovacuum_enabled = false);
```

## ALTER TABLE Operations

### SET SCHEMA

Move a table between schemas:

```sql
ALTER TABLE users SET SCHEMA app;
```

### SET LOGGED / SET UNLOGGED

Toggle between logged and unlogged modes:

```sql
ALTER TABLE users SET LOGGED;
ALTER TABLE users SET UNLOGGED;
```

`SET LOGGED` converts an unlogged table back to logged mode (all data is written to WAL).

### ALTER COLUMN SET STATISTICS

Set column-level statistics target:

```sql
ALTER TABLE users ALTER COLUMN email SET STATISTICS 500;
```

Higher values improve query planner estimates for columns with non-uniform distributions. Values range from `-1` (use default) to `10000`.

### ALTER COLUMN SET (attribute_option)

Set column-level attribute options:

```sql
ALTER TABLE users ALTER COLUMN email SET (n_distinct = 0.01);
ALTER TABLE users ALTER COLUMN email RESET (n_distinct);
```

Common attribute options: `n_distinct`, `n_distinct_inherited`.

### CLUSTER

Cluster a table based on an index:

```sql
ALTER TABLE users CLUSTER ON ix_users_email;
```

### ENABLE / DISABLE TRIGGER

Control trigger execution:

```sql
ALTER TABLE users DISABLE TRIGGER trg_users_updated_at;
ALTER TABLE users ENABLE TRIGGER trg_users_updated_at;
ALTER TABLE users ENABLE REPLICA TRIGGER trg_users_updated_at;
ALTER TABLE users ENABLE ALWAYS TRIGGER trg_users_updated_at;
```

### TRUNCATE

```sql
TRUNCATE TABLE users;
TRUNCATE TABLE users, posts CASCADE;
```

`TRUNCATE` is not generated by `make-migrations` but can be run manually for bulk data removal.

### Temporary Tables

Temporary tables use `ON COMMIT` for cleanup behaviour:

```sql
CREATE TEMPORARY TABLE temp_data (id int) ON COMMIT DELETE ROWS;
```

Supported `ON COMMIT` values:

| Value | Behaviour |
|-------|-----------|
| `PRESERVE ROWS` | Default: rows persist across transaction boundaries |
| `DELETE ROWS` | All rows deleted at transaction end |
| `DROP` | Table dropped at transaction end |

### LIKE Clause

Create a table with the same structure as an existing one:

```sql
CREATE TABLE users_archive (LIKE users INCLUDING ALL);
```

`INCLUDING ALL` copies defaults, constraints, indexes, and storage. This is a DDL operation (no data copied).
### Storage Params

`pg_storage_params` stores raw PostgreSQL table storage options. `pg_fillfactor` is kept as a shorthand and is folded into `pg_storage_params["fillfactor"]` during discovery.

```python
class Meta(PGTableMeta):
    pg_storage_params = {
        "fillfactor": 80,
        "autovacuum_enabled": "false",
    }
```

Generated DDL:

```sql
ALTER TABLE users SET (fillfactor = 80, autovacuum_enabled = false);
```
## Snapshot Format

### Column Extras

```json
{
  "name": "bio",
  "type": "text",
  "pg_column": {
    "collation": "en_US.UTF-8",
    "storage": "EXTENDED",
    "compression": "pglz",
    "generated": null,
    "identity": "always",
    "identity_start": 1,
    "identity_increment": 1
  }
}
```

### Table Extras

```json
{
  "pg_table": {
    "pg_fillfactor": 80,
    "pg_tablespace": "fastspace",
    "pg_unlogged": false,
    "pg_inherits": "base_entity",
    "pg_partition": {
      "strategy": "RANGE",
      "columns": ["created_at"]
    },
    "pg_excludes": [
      {"name": "excl_room_booking", "expression": "EXCLUDE USING gist (room_id WITH =, during WITH &&)"}
    ]
  }
}
```

## Reverse Engineering

`generate-models` queries `pg_class`, `pg_attribute`, `pg_constraint`, `pg_inherits`, `pg_tablespace`, `pg_partitioned_table`, and `pg_collation` to reverse-engineer all metadata.

```bash
$ dbwarden generate-models -d primary
```

Generated output for a table with identity, storage, compression, collation, and fillfactor:

```python
class User(Base):
    __tablename__ = "users"

    id:    Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio:   Mapped[str | None] = mapped_column(Text, nullable=True)

    class Meta(PGTableMeta):
        comment = "Core user accounts"
        pg_fillfactor = 80

        class id(PGColumnMeta):
            pg = pg.field(identity="always", identity_start=100, identity_increment=1)

        class bio(PGColumnMeta):
            pg = pg.field(storage="EXTENDED", compression="pglz", collation="en_US.UTF-8")
```

For a partitioned table:

```python
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    class Meta(PGTableMeta):
        pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
```
