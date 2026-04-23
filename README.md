<div align="center">

<img src="https://raw.githubusercontent.com/emiliano-gandini-outeda/DBWarden/refs/heads/main/assets/icon.png" width="128" height="128" style="border-radius: 20px;">

# DBWarden

A database migration system for Python/SQLAlchemy projects.

<a href="https://emiliano-gandini-outeda.github.io/DBWarden/">
  <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation">
</a>
<a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden">
  <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
</a>

---

<img src="https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/assets/banner.png?raw=true" width="100%">

</div>

## Installation

```bash
pip install dbwarden
```

## Configuration

**⚠️ Warning**

This is an experimental package. Your fuckups are not mine to fix. You have been warned.

*Even though this is an experimental package, I added lots of failsafes to protect the connected DB as to avoid issues.*

Create `warden.toml` in your project:

```toml
# Default database
default = "primary"

# Database configurations
[database.primary]
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./development.db"
dev_database_type = "sqlite"
dev_database_url = "sqlite:///./dev.db"

[database.analytics]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/analytics"
```

## Basic Commands

| Command | Description |
|---------|-------------|
| `dbwarden init` | Initialize migrations directory |
| `dbwarden database list` | List all configured databases |
| `dbwarden database add <name>` | Add a new database |
| `dbwarden make-migrations "name"` | Generate SQL from SQLAlchemy models |
| `dbwarden migrate` | Apply pending migrations |
| `dbwarden migrate -d <name>` | Migrate specific database |
| `dbwarden --dev migrate -d <name>` | Migrate using development DB URL |
| `dbwarden migrate --all` | Migrate all databases |
| `dbwarden rollback` | Revert the last migration |
| `dbwarden history` | Show migration history |
| `dbwarden status` | Show current status |

## Multi-Database Support

Manage multiple databases from a single configuration:

```bash
# Add databases
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"
dbwarden database add legacy --url "mysql://user:pass@localhost:3306/legacy"

# List all databases
dbwarden database list

# Migrate specific database
dbwarden migrate -d analytics

# Migrate all databases (sequentially)
dbwarden migrate --all
```

## SQLAlchemy Models

DBWarden automatically detects models in `models/`:

```python
# models/user.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(255), unique=True)
```

## Complete Example

```bash
# 1. Initialize
dbwarden init

# 2. Create models in models/

# 3. Add more databases
dbwarden database add analytics --url "postgresql://user:pass@localhost:5432/analytics"

# 4. Generate migration from models
dbwarden make-migrations "create users table"

# 5. Apply
dbwarden migrate --verbose

# 6. Migrate all databases
dbwarden migrate --all

# 7. View history
dbwarden history
```

## Supported Databases

| Database | Type Value | Features |
|----------|------------|----------|
| PostgreSQL | `postgresql` | SERIAL, TIMESTAMP, BYTEA |
| MySQL | `mysql` | AUTO_INCREMENT, ENUM |
| SQLite | `sqlite` | Built-in, zero config |
| ClickHouse | `clickhouse` | Analytics, MergeTree |
| MariaDB | `mariadb` | MySQL-compatible |

## Docs

For more information, see [DBWarden Docs](http://emiliano-gandini-outeda.me/DBWarden/) or [DBWarden DeepWiki page](https://deepwiki.com/emiliano-gandini-outeda/DBWarden)

## License

This Project is Licensed under the MIT License. See [LICENSE](https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE)
