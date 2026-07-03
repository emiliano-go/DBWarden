---
description: 'Learn how to configure DBWarden for single and multi-database setups:
  connection URLs, model discovery, dev mode with SQLite translation, credential management,
  and production patterns.'
seo:
  title: Configuration - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/configuration
  robots: index,follow
  og:
    type: website
    title: Configuration - DBWarden Documentation
    description: 'Learn how to configure DBWarden for single and multi-database setups:
      connection URLs, model discovery, dev mode with SQLite translation, credential
      management, and production patterns.'
    url: https://dbwarden.emiliano-go.com/configuration
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:width: 1376
    image:height: 768
    image:alt: DBWarden documentation
    site_name: DBWarden Documentation
    locale: en_US
  twitter:
    card: summary_large_image
    title: Configuration - DBWarden Documentation
    description: 'Learn how to configure DBWarden for single and multi-database setups:
      connection URLs, model discovery, dev mode with SQLite translation, credential
      management, and production patterns.'
    image: https://dbwarden.emiliano-go.com/assets/images/og-image.png
    image:alt: DBWarden documentation
    site: '@emiliano_go_'
  description: 'Learn how to configure DBWarden for single and multi-database setups:
    connection URLs, model discovery, dev mode with SQLite translation, credential
    management, and production patterns.'
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: Configuration - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/configuration
    description: 'Learn how to configure DBWarden for single and multi-database setups:
      connection URLs, model discovery, dev mode with SQLite translation, credential
      management, and production patterns.'
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
      name: Configuration
      item: https://dbwarden.emiliano-go.com/configuration
seo_html: "<title>Configuration - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Learn how to configure DBWarden for single and multi-database setups:\
  \ connection URLs, model discovery, dev mode with SQLite translation, credential\
  \ management, and production patterns.\">\n<link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/configuration\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"Configuration - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Learn how to configure DBWarden for\
  \ single and multi-database setups: connection URLs, model discovery, dev mode with\
  \ SQLite translation, credential management, and production patterns.\">\n<meta\
  \ property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/configuration\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta property=\"og:image:width\" content=\"1376\">\n<meta property=\"og:image:height\"\
  \ content=\"768\">\n<meta property=\"og:image:alt\" content=\"DBWarden documentation\"\
  >\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\">\n<meta property=\"\
  og:locale\" content=\"en_US\">\n<meta name=\"twitter:card\" content=\"summary_large_image\"\
  >\n<meta name=\"twitter:title\" content=\"Configuration - DBWarden Documentation\"\
  >\n<meta name=\"twitter:description\" content=\"Learn how to configure DBWarden\
  \ for single and multi-database setups: connection URLs, model discovery, dev mode\
  \ with SQLite translation, credential management, and production patterns.\">\n\
  <meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  >\n<meta name=\"twitter:image:alt\" content=\"DBWarden documentation\">\n<meta name=\"\
  twitter:site\" content=\"@emiliano_go_\">\n<script type=\"application/ld+json\"\
  >\n[\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"WebPage\"\
  ,\n    \"name\": \"Configuration - DBWarden Documentation\",\n    \"url\": \"https://dbwarden.emiliano-go.com/configuration\"\
  ,\n    \"description\": \"Learn how to configure DBWarden for single and multi-database\
  \ setups: connection URLs, model discovery, dev mode with SQLite translation, credential\
  \ management, and production patterns.\",\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  ,\n    \"publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"\
  Emiliano Gandini Outeda\",\n      \"logo\": \"https://dbwarden.emiliano-go.com/assets/images/og-image.png\"\
  \n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"@type\": \"\
  BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\": \"ListItem\"\
  ,\n        \"position\": 1,\n        \"name\": \"Configuration\",\n        \"item\"\
  : \"https://dbwarden.emiliano-go.com/configuration\"\n      }\n    ]\n  }\n]\n</script>\n"
---

# Configuration

DBWarden uses Python-based configuration with `database_config()` to define your databases.

**One configuration source** for migrations, CLI tools, and runtime: no split configs.

## Quick Start

The simplest configuration possible:

```python
# dbwarden.py
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url_sync="sqlite:///./app.db",
)
```

That's it! **4 parameters** to get started.

Run your first migration:

```bash
$ dbwarden init
$ dbwarden make-migrations "initial schema"
$ dbwarden migrate
```

## Learning Path

### New to DBWarden?
Start here to understand configuration basics:

1. **[Quick Start](quick-start.md)** - Your first configuration in 2 minutes
2. **[Concepts](concepts.md)** - How configuration works
3. **[Connection URLs](connection-urls.md)** - Database connection formats

### Building Your Configuration
Learn specific features:

- **[Model Discovery](model-discovery.md)** - How DBWarden finds your SQLAlchemy models
- **[Dev Mode](dev-mode.md)** - Local development with SQLite
- **[Multi-Database](multi-database.md)** - Configure multiple databases

### Production Ready
Deploy with confidence:

- **[Production Patterns](production-patterns.md)** - Real-world examples
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### Complete Reference
- **[Configuration API](../reference/configuration-api.md)** - Complete function signature and parameters

## Key Features

###  Simple Configuration

Define once, use everywhere:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
    model_paths=["app.models"],
)
```

###  Dev Mode

Use SQLite locally, PostgreSQL in production:

```python
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
)
```

Run commands with `--dev`:

```bash
$ dbwarden --dev migrate
$ dbwarden --dev status
```

###  Multi-Database

Configure as many databases as you need:

```python
# Primary database
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/main",
    model_paths=["app.models.primary"],
)

# Analytics database
analytics = database_config(
    database_name="analytics",
    database_type="clickhouse",
    database_url_sync="http://localhost:8123/analytics",
    model_paths=["app.models.analytics"],
)
```

###  Security First

Keep credentials out of code:

```python
import os

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=os.getenv("DATABASE_URL"),
    secure_values=True,  # Hide credentials in output
)
```

###  Validation

DBWarden validates your configuration:

-  Exactly one `default=True`
-  Unique database names
-  No duplicate URLs
-  Required `model_paths` for multi-database
-  Consistent dev mode configuration

## Configuration Loading

DBWarden discovers your configuration automatically:

1. **Looks for `dbwarden.py`** in current directory or parents
2. **Checks `DBWARDEN_CONFIG_MODULE`** environment variable
3. **Scans for `database_config()` calls** in your codebase (full project tree walk)
4. **Looks for `warden.toml`** as an alternative TOML-based config file

`dbwarden.py` is the default convention and the file created by `dbwarden init`, but `database_config(...)` can live in any discovered Python file inside your project.

## Common Patterns

### Single Database (Minimal)

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
)
```

### With Dev Mode (Recommended)

```python
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/myapp",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./dev.db",
    model_paths=["app.models"],
)
```

### Multiple Databases

```python
from dbwarden import database_config

# Primary
primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://localhost/main",
    model_paths=["app.models.primary"],
)

# Analytics
analytics = database_config(
    database_name="analytics",
    database_type="postgresql",
    database_url_sync="postgresql://localhost/analytics",
    model_paths=["app.models.analytics"],
)
```

### Production with Environment Variables

```python
import os
from dbwarden import database_config

primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync=os.getenv("DATABASE_URL"),
    model_paths=["app.models"],
    secure_values=True,
)
```

## Why Python Configuration?

**vs TOML/YAML/INI:**
-  Type checking with your IDE
-  Dynamic configuration (loops, conditionals)
-  Environment variable integration
-  No schema mismatches
-  Can compute values

**vs Environment Variables Only:**
-  Version controlled
-  Self-documenting
-  Validation at load time
-  Multiple databases easy
-  Can reference code structures

## What's Next?

Ready to configure your first database? Start here:

- **[Quick Start](quick-start.md)** - Build your first configuration
- **[Concepts](concepts.md)** - Understand how it works
- **[Production Patterns](production-patterns.md)** - Real-world examples

Already familiar with configuration? Jump to:

- **[Connection URLs](connection-urls.md)** - URL format reference
- **[Troubleshooting](troubleshooting.md)** - Common issues
- **[Configuration API](../reference/configuration-api.md)** - Complete reference
