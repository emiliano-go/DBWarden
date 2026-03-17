<div align="center">

<img src="assets/icon.png" width="128" height="128" style="border-radius: 20px;">

# DBWarden

A database migration system for Python/SQLAlchemy projects.

<a href="https://emiliano-gandini-outeda.github.io/DBWarden/">
  <img src="https://img.shields.io/badge/docs-mkdocs-blue.svg" alt="Documentation">
</a>
<a href="https://deepwiki.com/emiliano-gandini-outeda/DBWarden">
  <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
</a>

---

<img src="assets/banner.png" width="100%">

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
database_type = "sqlite"
sqlalchemy_url = "sqlite:///./development.db"
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
| `dbwarden config` | Show current configuration |
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


# models/click_events.py (ClickHouse example)
class ClickEvent(Base):
    __tablename__ = "click_events"
    __table_args__ = {
        "info": {
            "clickhouse_engine": "ReplacingMergeTree()",
            "clickhouse_order_by": "(event_id)",
            "clickhouse_partition_by": "toYYYYMM(occurred_at)",
            "clickhouse_settings": {"index_granularity": 64},
        }
    }

    event_id = Column(Integer, primary_key=True, info={"clickhouse_type": "UInt64"})
    payload = Column(String(255))
    occurred_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
```

The `info` dictionaries shown above allow you to pass ClickHouse-specific
instructions (engine, ORDER BY keys, codecs, TTLs, custom data types, etc.)
directly from SQLAlchemy models. When `database_type = "clickhouse"`, DBWarden
uses those hints while generating SQL.

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

# 6. Check configuration
dbwarden config
```

## Supported Databases

- PostgreSQL
- SQLite
- MySQL
- ClickHouse (beta)

### ClickHouse Quick Notes

- Install `clickhouse-connect` and set `database_type = "clickhouse"`.
- SQLAlchemy URL format: `clickhousedb+connect://user:password@host:8123/database`.
- Model metadata (`__table_args__['info']` or `Column(..., info={...})`) lets you
  define engines, `ORDER BY`, codecs, TTLs, and column-specific ClickHouse types.
- Repeatable migrations run using delete+insert semantics to stay idempotent.

## Docs

For more information, see [DBWarden Docs](http://emiliano-gandini-outeda.me/DBWarden/) or [DBWarden DeepWiki page](https://deepwiki.com/emiliano-gandini-outeda/DBWarden)

## License

This Project is Licensed under the MIT License. See [LICENSE](https://github.com/emiliano-gandini-outeda/DBWarden/blob/main/LICENSE)
