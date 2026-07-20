---
seo:
  title: Storage Parameters - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/storage-params
  robots: index,follow
  og:
    type: website
    title: Storage Parameters - DBWarden Documentation
    description: PostgreSQL supports table-level and index-level storage parameters
      that control physical storage behaviour, autovacuum tuning, and performance
      characteristics.
    url: https://dbwarden.emiliano-go.com/databases/postgresql/storage-params
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Storage Parameters - DBWarden Documentation
    description: PostgreSQL supports table-level and index-level storage parameters
      that control physical storage behaviour, autovacuum tuning, and performance
      characteristics.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: PostgreSQL supports table-level and index-level storage parameters
    that control physical storage behaviour, autovacuum tuning, and performance characteristics.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Storage Parameters - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/storage-params
    description: PostgreSQL supports table-level and index-level storage parameters
      that control physical storage behaviour, autovacuum tuning, and performance
      characteristics.
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
      name: Storage Params
      item: https://dbwarden.emiliano-go.com/databases/postgresql/storage-params
seo_html: "<title>Storage Parameters - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"PostgreSQL supports table-level and index-level storage\
  \ parameters that control physical storage behaviour, autovacuum tuning, and performance\
  \ characteristics.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql/storage-params\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Storage Parameters - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"PostgreSQL supports\
  \ table-level and index-level storage parameters that control physical storage behaviour,\
  \ autovacuum tuning, and performance characteristics.\">\n<meta property=\"og:url\"\
  \ content=\"https://dbwarden.emiliano-go.com/databases/postgresql/storage-params\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Storage Parameters - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"PostgreSQL supports table-level\
  \ and index-level storage parameters that control physical storage behaviour, autovacuum\
  \ tuning, and performance characteristics.\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Storage Parameters - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/storage-params\"\
  ,\n    \"description\": \"PostgreSQL supports table-level and index-level storage\
  \ parameters that control physical storage behaviour, autovacuum tuning, and performance\
  \ characteristics.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Storage Params\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/storage-params\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Storage Parameters

PostgreSQL supports table-level and index-level storage parameters that control physical storage behaviour, autovacuum tuning, and performance characteristics.

DBWarden tracks storage parameters through the `with_params` field on `PgIndexSpec` and table-level handlers.

## Table Storage Parameters

Set via `ALTER TABLE t SET (param = value, ...)` using the handler infrastructure.

### Autovacuum Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `autovacuum_enabled` | `bool` | Enables/disables autovacuum for this table | `True` |
| `autovacuum_vacuum_threshold` | `int` | Minimum number of dead tuples before vacuum | `50` |
| `autovacuum_vacuum_scale_factor` | `float` | Fraction of table dead tuples before vacuum | `0.2` |
| `autovacuum_vacuum_ins_threshold` | `int` | Minimum INSERT dead tuples before vacuum (PG 17+) | `1000` |
| `autovacuum_vacuum_ins_scale_factor` | `float` | Fraction of INSERT dead tuples before vacuum (PG 17+) | `0.2` |
| `autovacuum_analyze_threshold` | `int` | Minimum modified tuples before analyze | `50` |
| `autovacuum_analyze_scale_factor` | `float` | Fraction of modified tuples before analyze | `0.1` |
| `autovacuum_vacuum_cost_delay` | `int` | Millisecond delay between vacuum cost units | `2` |
| `autovacuum_vacuum_cost_limit` | `int` | Cost limit before vacuum pauses | `-1` (use global) |
| `autovacuum_freeze_min_age` | `int` | Minimum age before FREEZE | `50000000` |
| `autovacuum_freeze_max_age` | `int` | Maximum age before forced FREEZE | `200000000` |
| `autovacuum_freeze_table_age` | `int` | Age at which whole-table freeze is considered | `150000000` |
| `autovacuum_multixact_freeze_min_age` | `int` | Minimum multixact age before freeze | `5000000` |
| `autovacuum_multixact_freeze_max_age` | `int` | Maximum multixact age before forced freeze | `200000000` |
| `autovacuum_multixact_freeze_table_age` | `int` | Table-level multixact freeze age | `150000000` |

### Tuning Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `fillfactor` | `int` | Percentage of page space to fill (1-100) | `100` |
| `toast_tuple_target` | `int` | Minimum tuple size before TOAST (PG 11+) | `2048` |
| `parallel_workers` | `int` | Number of parallel workers for scans (PG 11+) | `0` (use global) |
| `vacuum_truncate` | `bool` | Allow vacuum to truncate empty pages (PG 14+) | `True` |
| `log_autovacuum_min_duration` | `int` | Log autovacuum actions exceeding this (ms) (PG 14+) | `-1` (disabled) |

### Table-Level Fillfactor

The `pg_fillfactor` attribute on `PGTableMeta` sets the fillfactor storage parameter:

```python
class Meta(PGTableMeta):
    pg_fillfactor = 80
```

```sql
ALTER TABLE users SET (fillfactor = 80);
```

Fillfactor applies per-table for heap storage and per-index for B-tree indexes. A lower fillfactor leaves more free space for future updates, reducing page splits at the cost of denser storage.

### Toast Tuple Target

Controls when inline values are moved to TOAST storage. Lower values move larger tuples to TOAST earlier:

```sql
ALTER TABLE users SET (toast_tuple_target = 1024);
```

## Index Storage Parameters

Set via the `with_params` field on `PgIndexSpec`:

```python
PgIndexSpec("ix_users_email", ["email"],
    with_params={"fillfactor": 70})
```

```sql
CREATE INDEX CONCURRENTLY ix_users_email ON users (email) WITH (fillfactor = 70);
```

### Access Method-Specific Parameters

| Access Method | Parameter | Type | Default | Description |
|---------------|-----------|------|---------|-------------|
| B-tree | `fillfactor` | `int` | `90` | Page fill percentage |
| GiST | `buffering` | `str \| bool` | `auto` | `on`, `off`, or `auto` |
| BRIN | `pages_per_range` | `int` | `128` | Pages per block range |
| BRIN | `autosummarize` | `bool` | `off` | Auto-summarize on insert |
| Hash | `fillfactor` | `int` | `100` | Page fill percentage |

Example: BRIN parameters:

```python
PgIndexSpec("ix_orders_created_at", ["created_at"],
    using="brin",
    with_params={"pages_per_range": 32, "autosummarize": True})
```

```sql
CREATE INDEX CONCURRENTLY ix_orders_created_at ON orders USING BRIN (created_at) WITH (pages_per_range = 32, autosummarize = on);
```

## Using `with_params`

The `with_params` field on `PgIndexSpec` accepts a dict of parameter name-value pairs:

| Field | Value Type | Description |
|-------|------------|-------------|
| Key | `str` | PostgreSQL storage parameter name (e.g. `fillfactor`, `autosummarize`) |
| Value | `str \| int \| bool` | Parameter value. Booleans render as `on`/`off` |

Parameters are rendered as `WITH (key1 = val1, key2 = val2, ...)` in the `CREATE INDEX` statement.

## Changing Storage Parameters

Storage parameter changes are detected during the DIFF phase. Parameter changes for tables and indexes produce `ALTER TABLE ... SET (...)` or `ALTER INDEX ... SET (...)` DDL. Safety classification varies:

| Change | Severity |
|--------|----------|
| fillfactor change | `INFO` |
| autovacuum setting change | `INFO` |
| BRIN parameter change | `INFO` |
| Index `with_params` change | `INFO` |

See [Migration Safety](migration-safety.md) for the full classification table.
