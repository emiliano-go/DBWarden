---
seo:
  title: Rolling Back - DBWarden Documentation
  description: Rolling Back Rollback executes the rollback section of applied migration
    files. What you'll learn how rollback selection works when to use count vs toversion
    how to recover safely when rollback fails...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/rolling-back/
  robots: index,follow
  og:
    type: website
    title: Rolling Back - DBWarden Documentation
    description: Rolling Back Rollback executes the rollback section of applied migration
      files. What you'll learn how rollback selection works when to use count vs toversion
      how to recover safely when rollback fails...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/rolling-back/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Rolling Back - DBWarden Documentation
    description: Rolling Back Rollback executes the rollback section of applied migration
      files. What you'll learn how rollback selection works when to use count vs toversion
      how to recover safely when rollback fails...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Rolling Back - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/rolling-back/
    description: Rolling Back Rollback executes the rollback section of applied migration
      files. What you'll learn how rollback selection works when to use count vs toversion
      how to recover safely when rollback fails...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Rolling Back

Rollback executes the `-- rollback` section of applied migration files.

## What you'll learn

- how rollback selection works
- when to use `--count` vs `--to-version`
- how to recover safely when rollback fails

## Prerequisites

- applied migration history exists
- rollback SQL is defined in target migration files

## Run it

```bash
dbwarden rollback --database primary
dbwarden rollback --database primary --count 2
dbwarden rollback --database primary --to-version 0007
```

## What happened

- DBWarden loads applied migration history
- selects rollback candidates
- executes rollback SQL in reverse order
- updates migration metadata records

## Common failure modes

- rollback SQL doesn't match current schema state
- data rollback assumptions are invalid
- lock conflicts from concurrent migration process

When rollback is risky, prefer a forward-fix migration.

Reference: [Safe Deployment](../advanced/safe-deployment.md)

See also: [Cookbook: Apply & Inspect](../cookbook/03-apply-and-inspect.md)

