# DBWarden

**DBWarden** is a professional database migration system for Python/SQLAlchemy projects.

## Installation

```bash
pip install dbwarden
```

## Configuration

Create `.env` in your project:

```env
STRATA_SQLALCHEMY_URL=postgresql://user:pass@localhost/db
STRATA_ASYNC=false  # or true for async mode
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
| `STRATA_SQLALCHEMY_URL` | DB connection URL |
| `STRATA_ASYNC` | Async mode (`true`/`false`) |
| `STRATA_MODEL_PATHS` | Paths to SQLAlchemy models |

## Supported Databases

- PostgreSQL (sync + async)
- SQLite (sync + async)
- MySQL (sync)

## License

MIT
