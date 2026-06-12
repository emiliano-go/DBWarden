---
description: Set up DBWarden in your project, install dependencies, initialize the project, define your first database, and verify that the configuration loads correctly.
seo:
  title: Setup - DBWarden Documentation
  description: Set up DBWarden in your project, install dependencies, initialize the project, define your first database, and verify that the configuration loads correctly.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/setup/
  robots: index,follow
  og:
    type: website
    title: Setup - DBWarden Documentation
    description: Set up DBWarden in your project, install dependencies, initialize the project, define your first database, and verify that the configuration loads correctly.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/setup/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Setup - DBWarden Documentation
    description: Set up DBWarden in your project, install dependencies, initialize the project, define your first database, and verify that the configuration loads correctly.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Setup - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/getting-started/setup/
    description: Set up DBWarden in your project, install dependencies, initialize the project, define your first database, and verify that the configuration loads correctly.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Setup

This guide shows the initial project setup for DBWarden. By the end, you will have DBWarden installed, a project-local config file, and one verified database entry.

## Requirements

- Python 3.12 or higher
- A project that uses SQLAlchemy models, or plans to
- A supported backend: PostgreSQL, MySQL, MariaDB, SQLite, or ClickHouse

## Install DBWarden

Install the base package:

```bash
pip install dbwarden
```

Optional dependency groups:

| Group | Command | Use case |
|---|---|---|
| `fastapi` | `pip install "dbwarden[fastapi]"` | FastAPI session dependencies and runtime integration |
| `metrics` | `pip install "dbwarden[metrics]"` | Prometheus metrics |
| `sandbox` | `pip install "dbwarden[sandbox]"` | Sandbox migration testing |

You can combine them:

```bash
pip install "dbwarden[fastapi,metrics,sandbox]"
```

## Initialize the Project

Run:

```bash
dbwarden init
```

Typical result:

```text
Initialized DBWarden project structure
Created migrations directory
Created dbwarden.py
```

`init` creates the local migration layout and a config scaffold. It is safe to run again, DBWarden will not destroy existing `database_config(...)` definitions.

## Create the Configuration File

The simplest `dbwarden.py` looks like this:

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/main",
    model_paths=["app.models"],
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

Copy this to your local `dbwarden.py`, then adjust the URLs and `model_paths` for your project.

## Step by Step

### Step 1: Import `database_config`

```python
from dbwarden import database_config
```

`database_config(...)` is the entry point for defining databases. Every configured database becomes part of the validated runtime config.

### Step 2: Define `database_name`

```python
database_name="primary"
```

This is the stable name you will use in CLI commands such as:

```bash
dbwarden status --database primary
```

### Step 3: Mark the default database

```python
default=True
```

Exactly one configured database must be the default. Commands without `--database` use that entry.

### Step 4: Set the backend type

```python
database_type="postgresql"
```

This controls backend-specific SQL generation, schema inspection, and metadata behavior.

Supported values:

- `postgresql`
- `mysql`
- `mariadb`
- `sqlite`
- `clickhouse`

### Step 5: Set the runtime URL

```python
database_url_sync="postgresql://user:password@localhost:5432/main"
```

This is the database URL used by CLI commands such as `make-migrations`, `migrate`, `status`, and `check`.

If your application also uses async SQLAlchemy sessions, you can define an async URL too:

```python
database_url_async="postgresql+asyncpg://user:password@localhost:5432/main"
```

DBWarden keeps sync and async URLs separate so the CLI and FastAPI runtime can share one config source without forcing a single driver choice.

### Step 6: Point to your models

```python
model_paths=["app.models"]
```

This tells DBWarden where to discover SQLAlchemy models. In multi-database projects, explicit `model_paths` are required.

### Step 7: Configure a dev database

```python
dev_database_type="sqlite"
dev_database_url="sqlite:///./development.db"
```

This is optional, but recommended. It lets you run commands locally with `--dev`, without touching your main database.

## Verify the Configuration

Run:

```text
$ dbwarden settings show --all
Database: primary
Type: postgresql
Default: true
Sync URL: postgresql://user:password@localhost:5432/main
Model paths: ['app.models']
Dev database type: sqlite
Dev database URL: sqlite:///./development.db
```

If this command works, DBWarden can resolve and validate your config.

## Common Problems

### `No configuration found`

DBWarden could not locate a config source. Make sure your project contains one discovered file with a `database_config(...)` call, usually `dbwarden.py`.

### `Exactly one default=True required`

If you configure more than one database, only one can be the default.

### `model_paths is required when more than one database is configured`

In multi-database setups, each database must declare the models that belong to it.

## Recap

You have:

- installed DBWarden
- initialized the project
- defined one typed database entry
- verified the config with `settings show`

Next, continue with [Modeling](modeling.md).
