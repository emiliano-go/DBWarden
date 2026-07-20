---
seo:
  title: Data operations - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations
  robots: index,follow
  og:
    type: website
    title: Data operations - DBWarden Documentation
    description: 'Data operations dataop are non-DDL statements that mutate data or
      trigger maintenance. They are not declared in the model: they are ad-hoc operations.'
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Data operations - DBWarden Documentation
    description: 'Data operations dataop are non-DDL statements that mutate data or
      trigger maintenance. They are not declared in the model: they are ad-hoc operations.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Data operations dataop are non-DDL statements that mutate data or
    trigger maintenance. They are not declared in the model: they are ad-hoc operations.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Data operations - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations
    description: 'Data operations dataop are non-DDL statements that mutate data or
      trigger maintenance. They are not declared in the model: they are ad-hoc operations.'
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
      name: Data Operations
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations
seo_html: "<title>Data operations - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Data operations dataop are non-DDL statements that mutate\
  \ data or trigger maintenance. They are not declared in the model: they are ad-hoc\
  \ operations.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Data operations - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Data operations dataop are non-DDL\
  \ statements that mutate data or trigger maintenance. They are not declared in the\
  \ model: they are ad-hoc operations.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Data operations - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Data operations dataop are non-DDL\
  \ statements that mutate data or trigger maintenance. They are not declared in the\
  \ model: they are ad-hoc operations.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Data operations - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations\"\
  ,\n    \"description\": \"Data operations dataop are non-DDL statements that mutate\
  \ data or trigger maintenance. They are not declared in the model: they are ad-hoc\
  \ operations.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Data Operations\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/data-operations\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Data operations

Data operations (`data_op()`) are non-DDL statements that mutate data or trigger maintenance. They are not declared in the model: they are ad-hoc operations.

## Additional model examples

### Batch partition cleanup

```python
# Freeze, back up, then drop old partitions
from dbwarden.databases.clickhouse import data_op

# Freeze for backup
for m in ["2023-01", "2023-02", "2023-03"]:
    data_op(f"ALTER TABLE events FREEZE PARTITION '{m}'")

# After backup verified, drop
for m in ["2023-01", "2023-02", "2023-03"]:
    data_op(f"ALTER TABLE events DROP PARTITION '{m}'")
```

### Conditional mutation with setting override

```python
# Large mutation with timeout
data_op("""
    ALTER TABLE events
        UPDATE status = 'archived'
        WHERE event_date < '2020-01-01'
        SETTINGS mutations_sync = 2
""")
```

### OPTIMIZE with deduplicate

```python
# Force full merge and deduplication on all parts
data_op("OPTIMIZE TABLE events FINAL DEDUPLICATE")

# With column-specific deduplication
data_op("OPTIMIZE TABLE events FINAL DEDUPLICATE BY id, event_date")
```

### Multi-step migration with data ops

```python
def migrate_events():
    # 1. Create new table via migrate
    # 2. Backfill from old partition
    data_op("""
        ALTER TABLE events_v2
            REPLACE PARTITION '2024-01'
            FROM events_v1
    """)
    # 3. Drop old partition
    data_op("ALTER TABLE events_v1 DROP PARTITION '2024-01'")
    # 4. Verify
    data_op("OPTIMIZE TABLE events_v2 FINAL")
```

## Partition operations

```python
from dbwarden.databases.clickhouse import data_op

# Attach a detached partition
data_op("ALTER TABLE events ATTACH PARTITION '2024-01'")

# Replace one partition with another
data_op("ALTER TABLE events REPLACE PARTITION '2024-02' FROM staging_events")

# Drop a partition
data_op("ALTER TABLE events DROP PARTITION '2024-01'")

# Clear column in partition
data_op("ALTER TABLE events CLEAR COLUMN payload IN PARTITION '2024-01'")

# Freeze partition for backup
data_op("ALTER TABLE events FREEZE PARTITION '2024-01'")

# Unfreeze
data_op("ALTER TABLE events UNFREEZE PARTITION '2024-01'")
```

## Mutations

```python
# DELETE
data_op("ALTER TABLE events DELETE WHERE event_date < '2023-01-01'")

# UPDATE
data_op("ALTER TABLE events UPDATE payload = 'redacted' WHERE id = 123")
```

## OPTIMIZE

```python
# Merge parts
data_op("OPTIMIZE TABLE events FINAL")

# With partition
data_op("OPTIMIZE TABLE events PARTITION '2024-01' FINAL")

# Deduplicate
data_op("OPTIMIZE TABLE events FINAL DEDUPLICATE")
```

## POPULATE

```python
# Populate a materialized view
data_op("ALTER TABLE mv_name POPULATE")
```

This is a data-op rather than a DDL property because it is a write concern, not structural. See [Materialized views](materialized-views.md).

## Secret rotation

Named collection secrets are rotated through ClickHouse's secret store:

```python
# Refresh credentials from secret store
data_op("ALTER NAMED COLLECTION kafka_prod UPDATE sasl_password = SECRET 'new_secret_id'")
```

## Safety

| Operation | Safety | Notes |
|-----------|--------|-------|
| ATTACH PARTITION | INFO | Cheap metadata operation |
| REPLACE PARTITION | WARN | Overwrites target |
| DROP PARTITION | WARN | Data loss within a partition |
| CLEAR COLUMN | WARN | Data cleared for partition |
| DELETE mutation | WARN | Async, causes part rewrites |
| UPDATE mutation | WARN | Async, causes part rewrites |
| OPTIMIZE FINAL | INFO | Heavy IO |
| POPULATE | INFO | Inserts current data |
| Secret rotation | INFO | |

## Rollback behavior

Data operations are **not reversible** by dbwarden: they are ad-hoc mutations. Plan accordingly: test on staging, back up partitions before DROP or REPLACE.
