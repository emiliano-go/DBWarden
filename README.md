<div align="center">

# DBWarden

A database migration system for Python/SQLAlchemy projects.

<a href="https://emiliano-gandini-outeda.github.io/DBWarden/">
  <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation">
</a>
<a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden">
  <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
</a>

</div>

## Installation

```bash
pip install dbwarden
```

## Configuration

Create `.env` in your project:

```env
DBWARDEN_SQLALCHEMY_URL=postgresql://user:pass@localhost/db
DBWARDEN_ASYNC=false  # or true for async mode
```

## Basic Commands

| Command | Description |
|---------|-------------|
| `dbwarden init` | Initialize migrations directory |
| `dbwarden make-migrations "name"` | Generate SQL from SQLAlchemy models |
| `dbwarden migrate` | Apply pending migrations |
| `dbwarden migrate --verbose` | Apply with detailed logging |
| `dbwarden rollback` | Revert the last migration |
| `dbwarden history` | Show migration history |
| `dbwarden status` | Show current status |
| `dbwarden mode` | Show sync/async mode |
| `dbwarden check-db` | Inspect DB schema |
| `dbwarden diff` | Show models vs DB differences |

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

# 3. Generate migration from models
dbwarden make-migrations "create users table"

# 4. Apply
dbwarden migrate --verbose

# 5. View history
dbwarden history
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DBWARDEN_SQLALCHEMY_URL` | DB connection URL |
| `DBWARDEN_ASYNC` | Async mode (`true`/`false`) |
| `DBWARDEN_MODEL_PATHS` | Paths to SQLAlchemy models |

## Supported Databases

- PostgreSQL (sync + async)
- SQLite (sync + async)
- MySQL (sync)

## Docs

For more information, see [DBWarden Docs](http://emiliano-gandini-outeda.me/DBWarden/)

## License

This Project is Licensed under the MIT License. See [LICENSE](https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE)
