---
seo:
  title: RLS & Policies - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies
  robots: index,follow
  og:
    type: website
    title: RLS & Policies - DBWarden Documentation
    description: 'Handler: PoliciesHandler DIFF phase'
    url: https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: RLS & Policies - DBWarden Documentation
    description: 'Handler: PoliciesHandler DIFF phase'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Handler: PoliciesHandler DIFF phase'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: RLS & Policies - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies
    description: 'Handler: PoliciesHandler DIFF phase'
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
      name: Rls And Policies
      item: https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies
seo_html: "<title>RLS &amp; Policies - DBWarden Documentation</title>\n<meta name=\"\
  description\" content=\"Handler: PoliciesHandler DIFF phase\">\n<link rel=\"canonical\"\
  \ href=\"https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"RLS &amp; Policies - DBWarden\
  \ Documentation\">\n<meta property=\"og:description\" content=\"Handler: PoliciesHandler\
  \ DIFF phase\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"RLS &amp; Policies - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Handler: PoliciesHandler DIFF phase\"\
  >\n<meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"RLS & Policies - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies\"\
  ,\n    \"description\": \"Handler: PoliciesHandler DIFF phase\",\n    \"image\"\
  : \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\",\n    \"publisher\"\
  : {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini Outeda\"\
  ,\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Databases\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/databases\"\n      },\n      {\n        \"\
  @type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"PostgreSQL\"\
  ,\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql\"\n\
  \      },\n      {\n        \"@type\": \"ListItem\",\n        \"position\": 3,\n\
  \        \"name\": \"Rls And Policies\",\n        \"item\": \"https://dbwarden.emiliano-go.com/databases/postgresql/rls-and-policies\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

# RLS & Policies

**Handler**: `PoliciesHandler` (DIFF phase)

Row-Level Security and policies are model-derived, declared on `PGTableMeta`.

## Enabling RLS

```python
class Meta(PGTableMeta):
    pg_rls = True
```

Generated DDL:
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### Default Deny Behaviour

When RLS is enabled but no policy applies to the current user, the default behaviour is to **deny all access**. Every row is invisible for read operations, and all write operations are blocked. At least one permissive policy must exist for the user to access data.

### FORCE / NO FORCE

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_rls_force = True
```

Generated DDL:
```sql
ALTER TABLE users FORCE ROW LEVEL SECURITY;
```

To disable force (without disabling RLS):

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_rls_force = False
```

```sql
ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
```

The force flag only emits when it explicitly changes. If `pg_rls_force` is absent or `False` on both the snapshot and model sides, no `FORCE`/`NO FORCE` DDL is generated. This avoids churn on indexes that only toggle RLS without changing force.

`FORCE ROW LEVEL SECURITY` applies RLS to the table owner, who would normally bypass it. `NO FORCE` (default) exempts the owner.

## Policies

Policies are declared as a list on `PGTableMeta`:

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_policies = [
        {
            "name": "tenant_isolation",
            "using": "tenant_id = current_setting('app.tenant_id')::int",
            "roles": ["app_user"],
            "permissive": True,
        },
    ]
```

### Policy Keys

| Key | Description |
|-----|-------------|
| `name` | Policy name |
| `using` | `USING` expression (row visibility) |
| `with_check` | `WITH CHECK` expression (row modification) |
| `roles` | Roles the policy applies to (absent = all roles) |
| `permissive` | `PERMISSIVE` (default) or `RESTRICTIVE` |
| `command` | `ALL` (default), `SELECT`, `INSERT`, `UPDATE`, `DELETE` |

### Permissive vs Restrictive

Multiple policies interact differently based on their type:

| Policy Type | Combination Logic |
|-------------|-------------------|
| `PERMISSIVE` (default) | **OR**: access is granted if ANY permissive policy allows it |

| `RESTRICTIVE` | **AND**: access is denied if ANY restrictive policy blocks it |
Restrictive policies filter results after permissive policies. Use restrictive policies to implement mandatory access controls that override permissive policies:

```python
pg_policies = [
    # Permissive: tenant-level access
    {"name": "tenant_access", "using": "tenant_id = current_setting('app.tenant_id')::int",
     "permissive": True},
    # Restrictive: block access to sensitive rows regardless of tenant
    {"name": "block_sensitive", "using": "NOT is_sensitive",
     "permissive": False, "command": "SELECT"},
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Add policy | `CREATE POLICY name ON table FOR command USING (expr)` |
| Alter policy | `ALTER POLICY name ON table USING (new_expr)` |
| Drop policy | `DROP POLICY IF EXISTS name ON table` |
| Enable RLS | `ALTER TABLE table ENABLE ROW LEVEL SECURITY` |
| Disable RLS | `ALTER TABLE table DISABLE ROW LEVEL SECURITY` |
| Force RLS | `ALTER TABLE table FORCE ROW LEVEL SECURITY` |
| Remove force | `ALTER TABLE table NO FORCE ROW LEVEL SECURITY` |

## BYPASSRLS Role Attribute

The `BYPASSRLS` role attribute lets a role bypass all RLS policies:

```python
pg_roles=[
    {"name": "admin_user", "login": True, "bypassrls": True},
]
```

This is equivalent to running without RLS for that role. See [Grants & Roles](grants-and-roles.md) for role configuration.

## RLS and COPY

`COPY TO` on a table with RLS respects policies; only rows visible through the user's policies are exported. `COPY FROM` on a table with RLS checks `WITH CHECK` policies for each inserted row.

## RLS and Unique Constraints

Unique constraints (including PKs) are **not** RLS-aware. A user may see a unique constraint violation caused by a row they cannot see. This is a PostgreSQL limitation: RLS filters query results but does not filter constraint enforcement.

## RLS and FK Constraints

Foreign key constraints are enforced server-side regardless of RLS. A user may not be able to `SELECT` a referenced row but can still insert a referencing row if the FK validates.

## Migration Safety

| Change | Severity |
|--------|----------|
| Enable RLS | `INFO` |
| Disable RLS | `WARNING` |
| Force RLS | `INFO` |
| Add policy | `INFO` |
| Drop policy | `INFO` |
| Change policy expression | `INFO` |

See [Migration Safety](migration-safety.md) for the full classification table.
