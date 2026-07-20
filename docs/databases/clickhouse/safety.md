---
seo:
  title: Safety classification - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/safety
  robots: index,follow
  og:
    type: website
    title: Safety classification - DBWarden Documentation
    description: Every change dbwarden detects is classified. Destructive operations
      require --force and emit warnings with reasons.
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/safety
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Safety classification - DBWarden Documentation
    description: Every change dbwarden detects is classified. Destructive operations
      require --force and emit warnings with reasons.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: Every change dbwarden detects is classified. Destructive operations
    require --force and emit warnings with reasons.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Safety classification - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/safety
    description: Every change dbwarden detects is classified. Destructive operations
      require --force and emit warnings with reasons.
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
      name: ClickHouse
      item: https://dbwarden.emiliano-go.com/databases/clickhouse
    - '@type': ListItem
      position: 3
      name: Safety
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/safety
seo_html: "<title>Safety classification - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Every change dbwarden detects is classified. Destructive\
  \ operations require --force and emit warnings with reasons.\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/safety\">\n<meta\
  \ name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Safety classification - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Every change dbwarden\
  \ detects is classified. Destructive operations require --force and emit warnings\
  \ with reasons.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/safety\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Safety classification - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Every change dbwarden detects is\
  \ classified. Destructive operations require --force and emit warnings with reasons.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Safety classification - DBWarden Documentation\",\n    \"url\"\
  : \"https://dbwarden.emiliano-go.com/databases/clickhouse/safety\",\n    \"description\"\
  : \"Every change dbwarden detects is classified. Destructive operations require\
  \ --force and emit warnings with reasons.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Safety\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/safety\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Safety classification

Every change dbwarden detects is classified. Destructive operations require `--force` and emit warnings with reasons.

## Classification levels

| Level | Color | Behavior |
|-------|-------|----------|
| `INFO` | Green | Applied automatically. Safe metadata changes: ADD COLUMN, ADD INDEX, ADD PROJECTION, SETTING changes, TTL changes. |
| `WARN` | Yellow | Applied automatically but logged as a warning. Attention recommended: DROP COLUMN, DROP TABLE, DROP INDEX, mutations, partition DROP/REPLACE. |
| `CRITICAL` | Red | Skipped unless `--force` is passed. Requires explicit acknowledgement: engine changes, ORDER BY non-extension, PRIMARY KEY changes, MV TO target change, type incompatibility, LowCardinality/Nullable toggle. |

## The `--force` flag

```bash
# Preview what would run
dbwarden make-migrations --plan --force -d analytics

# Apply with force
dbwarden migrate --force -d analytics
```

`--force` is all-or-nothing for CRITICAL items in the plan. There is no per-item override.

## The recreate pipeline

When a CRITICAL change requires a full table rebuild, dbwarden executes:

```
DETACH TABLE source
CREATE TABLE source_new (...new definition...)
INSERT INTO source_new SELECT * FROM source
RENAME TABLE source TO source_old,
             source_new TO source
ATTACH TABLE source_old
```

Steps:
1. **DETACH**: unmounts the table metadata from the database (data remains on disk)
2. **CREATE new**: creates a table with the new definition
3. **INSERT INTO ... SELECT**: copies all data from old to new (blocking if `source` is still receiving writes)
4. **RENAME**: atomically swaps source and source_old under an exclusive lock
5. **ATTACH**: remounts the old table as a backup under its new name

After the pipeline, `source` has the new definition and `source_old` holds the original data. Verification steps:

```sql
SELECT count(*) FROM source
SELECT engine, create_table_query FROM system.tables WHERE name = 'source'
```

If something went wrong, swap back:

```sql
RENAME TABLE source TO source_broken,
             source_old TO source
```

## Rollback of a recreate

The rollback is the reverse pipeline:

```
DETACH TABLE source_old
CREATE TABLE source (...original definition...)
INSERT INTO source SELECT * FROM source_old
RENAME TABLE source TO source_old2,
             source_old TO source
ATTACH TABLE source_old2
```

This restores the original table and keeps the failed new table as `source_old2`.

## When to use `--force`

- **Staging/testing**: always use `--force` to verify the pipeline works
- **Production small tables** (< 40 GB): `--force` with a maintenance window
- **Production large tables** (> 40 GB): avoid `--force`. Instead, manually plan a zero-downtime migration using `clickhouse-copier` or double-write during backfill

## Additional model examples

### Model that triggers CRITICAL classification

```python
# Current table for reference:
class OldEvents(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column()
    class Meta(CHTableMeta):
        ch = ch_table(engine=merge_tree(), order_by=["event_date", "id"])

# Change: remove a column from ORDER BY (non-extension)
class UpdatedEvents(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column()
    class Meta(CHTableMeta):
        ch = ch_table(engine=merge_tree(), order_by=["event_date"])  # 'id' removed
```

Plan output:

```
CRITICAL: Changing ORDER BY from (event_date, id) to (event_date) requires --force
Apply with: dbwarden migrate --force -d analytics
```

### Safe change that passes without --force

```python
# Add a column and extend ORDER BY
class SafeEvents(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_date: Mapped[date] = mapped_column()
    status: Mapped[str] = mapped_column()
    class Meta(CHTableMeta):
        ch = ch_table(engine=merge_tree(), order_by=["event_date", "id", "status"])
```

Plan output:

```
ALTER TABLE events ADD COLUMN status String   (INFO)
ALTER TABLE events MODIFY ORDER BY (event_date, id, status)   (INFO)
```

### Recreate pipeline example with verification

```bash
# 1. Preview the recreate
$ dbwarden make-migrations --plan --force -d analytics

# 2. Apply
$ dbwarden migrate --force -d analytics

# 3. Verify the new table
$ clickhouse-client -q "SELECT count(*) FROM events"
$ clickhouse-client -q "SELECT engine, create_table_query FROM system.tables WHERE name = 'events'"

# 4. If rollback needed:
$ clickhouse-client -q "RENAME TABLE events TO events_broken, events_old TO events"
```

## ClickHouse-native safety features

dbwarden also respects ClickHouse's server-side `allow_ddl` and `readonly` settings. If the server refuses a DDL statement, dbwarden logs the error and continues with the remaining plan items.
