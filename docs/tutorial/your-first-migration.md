---
description: Create your first SQL migration with DBWarden. Learn how to generate
  upgrade and rollback SQL from SQLAlchemy models, apply migrations, and verify database
  state.
seo:
  title: Your First Migration - DBWarden Documentation
  description: Create your first SQL migration with DBWarden. Learn how to generate
    upgrade and rollback SQL from SQLAlchemy models, apply migrations, and verify
    database state.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/your-first-migration/
  robots: index,follow
  og:
    type: website
    title: Your First Migration - DBWarden Documentation
    description: Create your first SQL migration with DBWarden. Learn how to generate
      upgrade and rollback SQL from SQLAlchemy models, apply migrations, and verify
      database state.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/your-first-migration/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Your First Migration - DBWarden Documentation
    description: Create your first SQL migration with DBWarden. Learn how to generate
      upgrade and rollback SQL from SQLAlchemy models, apply migrations, and verify
      database state.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Your First Migration - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/your-first-migration/
    description: Create your first SQL migration with DBWarden. Learn how to generate
      upgrade and rollback SQL from SQLAlchemy models, apply migrations, and verify
      database state.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Your First Migration

Create your first migration from SQLAlchemy models.

## What you'll learn

- how to generate a versioned migration file
- how to review upgrade/rollback sections
- when to create manual migrations

## Prerequisites

- configuration loads successfully (`dbwarden settings show --all`)
- target database has model paths configured
- model metadata reflects intended change

## Generate migration

```bash
dbwarden make-migrations "create users table" --database primary
```

Typical output file:

```text
migrations/primary/primary__0001_create_users_table.sql
```

## Review the file

Every migration must include both sections:

```sql
-- upgrade

-- rollback
```

## Manual migration option

When change is not model-driven:

```bash
dbwarden new "manual hotfix" --database primary
```

## Validate migration quality

```bash
dbwarden migrate --database primary
dbwarden rollback --database primary --count 1
dbwarden migrate --database primary
```

See also: [Cookbook: Models & Migrations](../cookbook/02-models-and-migrations.md)

