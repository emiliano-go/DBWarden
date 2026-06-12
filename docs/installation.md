---
seo:
  title: Installation - DBWarden Documentation
  description: This guide covers installing DBWarden in your project and verifying
    it works correctly.
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/installation/
  robots: index,follow
  og:
    type: website
    title: Installation - DBWarden Documentation
    description: This guide covers installing DBWarden in your project and verifying
      it works correctly.
    url: https://emiliano-gandini-outeda.github.io/DBWarden/installation/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: Installation - DBWarden Documentation
    description: This guide covers installing DBWarden in your project and verifying
      it works correctly.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: Installation - DBWarden Documentation
    url: https://emiliano-gandini-outeda.github.io/DBWarden/installation/
    description: This guide covers installing DBWarden in your project and verifying
      it works correctly.
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# Installation

This guide covers installing DBWarden in your project and verifying it works correctly.

## Requirements

- Python 3.10 or higher
- A project that uses SQLAlchemy for database models
- pip or another Python package manager

## Install using pip

```bash
pip install dbwarden
```

### With poetry

If your project uses Poetry:

```bash
poetry add dbwarden
```

### Development dependencies

To also install testing and linting tools:

```bash
pip install "dbwarden[dev]"
```

Or with poetry:

```bash
poetry add --group dev dbwarden
```

### Optional dependency groups

| Group | Command | Provides |
|-------|---------|----------|
| `postgres` | `pip install "dbwarden[postgres]"` | PostgreSQL driver (`psycopg2-binary`) |
| `mysql` | `pip install "dbwarden[mysql]"` | MySQL/MariaDB driver (`pymysql`) |
| `clickhouse` | `pip install "dbwarden[clickhouse]"` | ClickHouse driver (`clickhouse-connect`) |
| `fastapi` | `pip install "dbwarden[fastapi]"` | FastAPI session dependencies, health router, migration router, metrics router, Redis lock |
| `metrics` | `pip install "dbwarden[metrics]"` | Prometheus metrics endpoint (`prometheus-client`) |
| `sandbox` | `pip install "dbwarden[sandbox]"` | Sandbox migration testing via testcontainers |

Combine groups as needed:

```bash
pip install "dbwarden[postgres,mysql,fastapi]"
```

## Database drivers

DBWarden uses SQLAlchemy under the hood. The recommended way to install drivers is via the extras above:

```bash
# PostgreSQL
pip install "dbwarden[postgres]"

# MySQL/MariaDB
pip install "dbwarden[mysql]"

# ClickHouse
pip install "dbwarden[clickhouse]"

# SQLite comes bundled with Python
```

You can also install drivers directly if you prefer:

```bash
pip install psycopg2-binary    # PostgreSQL
pip install pymysql            # MySQL / MariaDB
pip install clickhouse-connect # ClickHouse
```

## Verify installation

After installing, confirm DBWarden is available:

```bash
dbwarden version
```

You should see output:

```
0.9.4
```

## Initialize in your project

Create the DBWarden structure in your project directory:

```bash
dbwarden init
```

This creates:

- a `migrations/` directory structure
- a `dbwarden.py` config scaffold (or discovers your existing config source)

## What happens during init

When you run `init`, DBWarden:

1. Creates `migrations/` if missing
2. Creates `dbwarden.py` (or updates existing config source) with import scaffolding
3. Does not overwrite existing `database_config(...)` definitions you have added

You can run `init` safely on an existing project - it is idempotent.

## Quick configuration

After init, configure your first database by editing `dbwarden.py` (or your existing config file that contains `database_config(...)` calls):

```python
from dbwarden import database_config


primary = database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url_sync="postgresql://user:password@localhost:5432/mydb",
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

The `dev_database_*` fields are optional but recommended - they enable fast local iterations with `--dev`.

## Verify configuration loads

```bash
dbwarden settings show --all
```

You should see your database entry printed with type and URL.

## Common installation issues

**Command not found after pip install**

- Ensure your virtual environment is activated
- Try uninstalling and reinstalling: `pip uninstall dbwarden && pip install dbwarden`

**Import errors or missing module warnings**

- Upgrade pip and reinstall: `pip install --upgrade pip dbwarden`

**Database driver errors**

- Install the appropriate driver for your target database (see Database drivers section above)

## Upgrading

To update to a newer version:

```bash
pip install --upgrade dbwarden
```

Or with poetry:

```bash
poetry update dbwarden
```

Check the release notes when upgrading major versions - there may be configuration or workflow changes.

