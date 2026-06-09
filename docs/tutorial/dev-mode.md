---
seo:
  title: Dev Mode - DBWarden Documentation
  description: Dev Mode Dev mode runs commands against devdatabaseurl/devdatabasetype
    instead of productiontargeted values. What you'll learn how dev swaps active database
    settings how to configure dev database...
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/dev-mode/
  robots: index,follow
  og:
    type: website
    title: Dev Mode - DBWarden Documentation
    description: Dev Mode Dev mode runs commands against devdatabaseurl/devdatabasetype
      instead of productiontargeted values. What you'll learn how dev swaps active
      database settings how to configure dev database...
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/dev-mode/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Dev Mode - DBWarden Documentation
    description: Dev Mode Dev mode runs commands against devdatabaseurl/devdatabasetype
      instead of productiontargeted values. What you'll learn how dev swaps active
      database settings how to configure dev database...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Dev Mode - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/tutorial/dev-mode/
    description: Dev Mode Dev mode runs commands against devdatabaseurl/devdatabasetype
      instead of productiontargeted values. What you'll learn how dev swaps active
      database settings how to configure dev database...
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Dev Mode

Dev mode runs commands against `dev_database_url`/`dev_database_type` instead of production-targeted values.

## What you'll learn

- how `--dev` swaps active database settings
- how to configure dev database fields
- when to use `--strict-translation`

## Prerequisites

- database entry includes `dev_database_url`
- optionally `dev_database_type`

## Configure it

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:pass@localhost:5432/main",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

## Run it

```bash
dbwarden --dev make-migrations "sync models" --database primary
dbwarden --dev migrate --database primary
```

Strict translation mode:

```bash
dbwarden --dev --strict-translation make-migrations "validate" --database primary
```

## Common failure modes

- `--dev` without `dev_database_url`
- relying on backend-specific SQL features unavailable in SQLite
- ignoring strict translation errors in CI workflows

Reference: [SQL Translation](../sql-translation.md)

See also: [Cookbook: Project Setup](../cookbook/01-project-setup.md)

