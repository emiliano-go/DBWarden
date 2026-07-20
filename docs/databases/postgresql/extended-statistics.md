---
seo:
  title: Extended Statistics - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics
  robots: index,follow
  og:
    type: website
    title: Extended Statistics - DBWarden Documentation
    description: 'Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,
      PG 14+'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Extended Statistics - DBWarden Documentation
    description: 'Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,
      PG 14+'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,
    PG 14+'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Extended Statistics - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics
    description: 'Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,
      PG 14+'
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
      name: Extended Statistics
      item: https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics
seo_html: "<title>Extended Statistics - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,\
  \ PG 14+\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Extended Statistics - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Handler: ExtendedStatisticsHandler\
  \ PREAMBLE phase, config-driven, PG 14+\">\n<meta property=\"og:url\" content=\"\
  https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics\">\n<meta\
  \ property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Extended Statistics - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Handler: ExtendedStatisticsHandler\
  \ PREAMBLE phase, config-driven, PG 14+\">\n<meta name=\"twitter:image\" content=\"\
  https://dbwarden.emiliano-go.com/assets/images/og-image.png\">\n<meta name=\"twitter:image:alt\"\
  \ content=\"DBWarden documentation\">\n<meta name=\"twitter:site\" content=\"@emiliano_go_\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"Extended Statistics - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics\"\
  ,\n    \"description\": \"Handler: ExtendedStatisticsHandler PREAMBLE phase, config-driven,\
  \ PG 14+\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Extended Statistics\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/extended-statistics\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# Extended Statistics

**Handler**: `ExtendedStatisticsHandler` (PREAMBLE phase, config-driven, PG 14+)

Extended statistics give the query planner better estimates for correlated columns.

```python
pg_extended_statistics=[
    {
        "name": "stats_users_email_city",
        "table": "users",
        "kinds": ["d", "f"],
        "columns": "email, city",
    },
]
```

## Kind Codes

| Code | Kind | Description | PG Version |
|------|------|-------------|------------|
| `d` | ndistinct | Distinct-value counts for column groups | 10+ |
| `f` | dependencies | Functional dependency statistics | 10+ |
| `m` | MCV | Most-common-values lists | 10+ |
| `e` | expressions | Expression statistics (PG 14+) | 14+ |

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE STATISTICS name (kinds) ON columns FROM table;` |
| Alter | `ALTER STATISTICS name SET STATISTICS target;` |
| Drop | `DROP STATISTICS IF EXISTS name;` |
| Analyze | `ANALYZE table;` (required to populate statistics) |

### ALTER STATISTICS

The statistics target controls sample size. Higher values produce better estimates at the cost of longer `ANALYZE` time:

```sql
ALTER STATISTICS stats_users_email_city SET STATISTICS 1000;
```

Values range from `-1` (use system default, typically 100) to `10000`.

### ANALYZE Requirements

`CREATE STATISTICS` defines the statistics object but does not populate it. Run `ANALYZE` on the table to collect the first statistics sample:

```bash
$ dbwarden analyze -d primary  # If available via handler
```

## Examples

```python
# ndistinct + dependencies on correlated columns
{"name": "stats_order_date_status", "table": "orders",
 "kinds": ["d", "f"], "columns": "order_date, status"}

# MCV on a high-cardinality group
{"name": "stats_product_category", "table": "products",
 "kinds": ["m"], "columns": "category_id, price"}

# Expression statistics (PG 14+)
{"name": "stats_user_email_domain", "table": "users",
 "kinds": ["d", "m"], "expressions": ["lower(email)"]}
```

Generated DDL:
```sql
CREATE STATISTICS stats_users_email_city (ndistinct, dependencies) ON email, city FROM users;
```

## Schema Support

Extended statistics can be scoped to a schema:

```python
{"name": "stats_order_date_status", "table": "orders",
 "schema": "app", "kinds": ["d", "f"], "columns": "order_date, status"}
```

## Migration Safety

| Change | Severity |
|--------|----------|
| Add extended statistic | `INFO` |
| Drop extended statistic | `WARNING` |
| Change kinds / columns | `WARNING` |
| Change statistics target | `INFO` |

See [Migration Safety](migration-safety.md) for the full classification table.
