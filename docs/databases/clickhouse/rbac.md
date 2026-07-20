---
seo:
  title: RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/clickhouse/rbac
  robots: index,follow
  og:
    type: website
    title: RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden Documentation
    description: All RBAC objects are declared in the config layer via databaseconfig.
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/rbac
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden Documentation
    description: All RBAC objects are declared in the config layer via databaseconfig.
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: All RBAC objects are declared in the config layer via databaseconfig.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/clickhouse/rbac
    description: All RBAC objects are declared in the config layer via databaseconfig.
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
      name: Rbac
      item: https://dbwarden.emiliano-go.com/databases/clickhouse/rbac
seo_html: "<title>RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden\
  \ Documentation</title>\n<meta name=\"description\" content=\"All RBAC objects are\
  \ declared in the config layer via databaseconfig.\">\n<link rel=\"canonical\" href=\"\
  https://dbwarden.emiliano-go.com/databases/clickhouse/rbac\">\n<meta name=\"robots\"\
  \ content=\"index,follow\">\n<meta property=\"og:type\" content=\"website\">\n<meta\
  \ property=\"og:title\" content=\"RBAC (roles, users, policies, quotas, profiles,\
  \ grants) - DBWarden Documentation\">\n<meta property=\"og:description\" content=\"\
  All RBAC objects are declared in the config layer via databaseconfig.\">\n<meta\
  \ property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/clickhouse/rbac\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"RBAC (roles, users, policies, quotas,\
  \ profiles, grants) - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"All RBAC objects are declared in the config layer via databaseconfig.\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"RBAC (roles, users, policies, quotas, profiles, grants) - DBWarden\
  \ Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/rbac\"\
  ,\n    \"description\": \"All RBAC objects are declared in the config layer via\
  \ databaseconfig.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"ClickHouse\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Rbac\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/clickhouse/rbac\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# RBAC (roles, users, policies, quotas, profiles, grants)

All RBAC objects are declared in the config layer via `database_config()`.

## Config keys

```python
from dbwarden import database_config
from dbwarden.databases.clickhouse import (
    ch_role_spec, ch_user_spec, ch_row_policy_spec,
    ch_quota_spec, ch_settings_profile_spec, ch_grant_spec,
)

database_config(
    name="analytics",
    url="clickhouse://...",
    ch_roles=[...],
    ch_users=[...],
    ch_row_policies=[...],
    ch_quotas=[...],
    ch_settings_profiles=[...],
    ch_grants=[...],
)
```

## Roles

```python
ch_roles=[
    ch_role_spec(name="analyst"),
    ch_role_spec(name="admin"),
]
```

Generated DDL:

```sql
CREATE ROLE IF NOT EXISTS analyst;
CREATE ROLE IF NOT EXISTS admin;
```

No diff beyond name: roles are identifiers.

## Users

```python
ch_users=[
    ch_user_spec(
        name="alice",
        # Authentication: declare-only via named collection
        named_collection="ldap_prod",
        # Or directly (but values are not stored/compared):
        # identified_by="sha256_password", password="secret"
        default_role="analyst",
        settings={"max_memory_usage": 10000000000},
    ),
]
```

Generated DDL:

```sql
CREATE USER IF NOT EXISTS alice
DEFAULT ROLE analyst
SETTINGS max_memory_usage = 10000000000;
```

## Row policies

```python
ch_row_policies=[
    ch_row_policy_spec(
        name="analyst_filter",
        table="events",
        as_restriction="event_date >= '2024-01-01'",
    ),
]
```

Generated DDL:

```sql
CREATE ROW POLICY IF NOT EXISTS analyst_filter
ON events
AS PERMISSIVE
FOR SELECT USING event_date >= '2024-01-01'
TO analyst;
```

## Quotas

```python
ch_quotas=[
    ch_quota_spec(
        name="monthly_reads",
        interval={"month": [1000000, 0, 0]},
    ),
]
```

Generated DDL:

```sql
CREATE QUOTA IF NOT EXISTS monthly_reads
FOR INTERVAL 1 MONTH
MAX QUERIES 1000000, ERRORS 0, RESULT ROWS 0
TO analyst;
```

## Settings profiles

```python
ch_settings_profiles=[
    ch_settings_profile_spec(
        name="strict",
        settings={"max_memory_usage": 10000000000},
        constraints={"max_memory_usage": "READONLY"},
    ),
]
```

Generated DDL:

```sql
CREATE SETTINGS PROFILE IF NOT EXISTS strict
SETTINGS max_memory_usage = 10000000000 CONSTRAINED READONLY;
```

## Grants

```python
ch_grants=[
    ch_grant_spec(
        privileges=["SELECT", "INSERT"],
        on="analytics.events",
        to="analyst",
    ),
]
```

Generated DDL:

```sql
GRANT SELECT, INSERT ON analytics.events TO analyst;
```

## Additional model examples

### Complete RBAC config with multiple objects

```python
database_config(
    name="analytics",
    url="clickhouse://localhost:9000",
    ch_named_collections=[
        named_collection("ldap_corp", keys={"ldap_server": "ldap.corp.example.com"}),
    ],
    ch_roles=[
        ch_role_spec("readonly"),
        ch_role_spec("analyst"),
        ch_role_spec("admin"),
    ],
    ch_settings_profiles=[
        ch_settings_profile_spec(
            name="strict_read",
            settings={
                "max_memory_usage": 5000000000,
                "max_result_rows": 10000,
            },
            constraints={
                "max_memory_usage": "READONLY",
                "max_result_rows": "READONLY",
            },
        ),
    ],
    ch_users=[
        ch_user_spec(
            name="alice",
            named_collection="ldap_corp",
            default_role="analyst",
            settings_profile="strict_read",
        ),
        ch_user_spec(
            name="bob",
            identified_by="sha256_password",
            password="changeme",  # declare-only: not diffed after creation
            default_role="readonly",
        ),
    ],
    ch_row_policies=[
        ch_row_policy_spec(
            name="analyst_filter",
            table="analytics.events",
            as_restriction="event_date >= '2024-01-01'",
        ),
    ],
    ch_quotas=[
        ch_quota_spec(
            name="monthly_cap",
            interval={"month": [100000, 0, 0]},
        ),
    ],
    ch_grants=[
        ch_grant_spec(privileges=["SELECT"], on="analytics.*", to="readonly"),
        ch_grant_spec(privileges=["SELECT", "INSERT"], on="analytics.*", to="analyst"),
        ch_grant_spec(privileges=["ALL"], on="analytics.*", to="admin"),
    ],
)
```

### Dict config (raw path)

```python
database_config(
    name="analytics",
    url="clickhouse://localhost:9000",
    ch_roles=[{"name": "analyst"}, {"name": "engineer"}],
    ch_users=[{
        "name": "carol",
        "identified_by": "sha256_password",
        "password": "s3cret",
        "default_role": "engineer",
    }],
)
```

## `storage != 'users.xml'` filter

dbwarden refuses to manage roles, users, or any RBAC object stored in `users.xml`:

```
ERROR: Cannot manage RBAC objects stored in users.xml.
Set storage = 'replicated' or use ClickHouse-native RBAC.
```

This is checked at config load time. If the server reports that RBAC storage is `users.xml`, all RBAC operations are skipped with a clear error.

## Drop gating

`DROP USER`, `DROP ROLE`, etc. require `--clickhouse-allow-drop-rbac`:

```bash
dbwarden migrate -d analytics --clickhouse-allow-drop-rbac
```

Without it, RBAC drop statements are skipped:

```
INFO: RBAC drop skipped: use --clickhouse-allow-drop-rbac to enable
```

This prevents accidental deactivation of users during migration runs.

## What changes are allowed

| Change | Safety |
|--------|--------|
| Add RBAC object | INFO |
| Drop RBAC object | WARN (gated by `--clickhouse-allow-drop-rbac`) |
| Modify user settings | INFO |
| Modify grant set | INFO |
| Change row policy expression | WARN |
| Change quota interval | INFO |
| Change settings profile | INFO |
| Named collection swap | INFO |

## Rollback behavior

Every RBAC CREATE has a DROP rollback and vice versa. Settings changes revert via `ALTER USER ... SETTINGS ...`.
