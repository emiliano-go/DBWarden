# Supported Databases

DBWarden supports multiple database backends. This guide covers configuration and considerations for each.

## Overview

| Database | Supported | Driver Required |
|----------|-----------|-----------------|
| PostgreSQL | Yes | `psycopg2-binary` |
| MySQL | Yes | `mysql-connector-python` |
| SQLite | Yes | Built-in |
| ClickHouse | Beta | `clickhouse-connect` (HTTP) |

## PostgreSQL

### Connection URL

Add to your `warden.toml`:

```toml
database_type = "postgres"
sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"
```

**Requirements:**
```bash
pip install psycopg2-binary
```

### Features

- Full support for all PostgreSQL features
- UUID types
- JSON/JSONB columns
- Array types (via manual migration)
- Full-text search (via manual migration)
- PostgreSQL-specific constraints

### PostgreSQL Schema

Set default schema in `warden.toml`:

```toml
postgres_schema = "public"  # default
# or
postgres_schema = "custom_schema"
```

### Example PostgreSQL Migration

```sql
-- upgrade

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_ossp_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- rollback

DROP INDEX idx_users_email;
DROP TABLE users;
```

## MySQL

### Connection URL

Add to your `warden.toml`:

```toml
database_type = "mysql"
sqlalchemy_url = "mysql://user:password@localhost:3306/mydb"
```

**Requirements:**
```bash
pip install mysql-connector-python
```

### Features

- Full support for MySQL features
- ENUM types
- SET types
- Full-text indexes (MyISAM, InnoDB 5.6+)
- AUTO_INCREMENT

### Limitations

- Some PostgreSQL-specific types not available
- Different default string lengths

### Example MySQL Migration

```sql
-- upgrade

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    status ENUM('active', 'inactive', 'pending') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_users_email ON users(email);

-- rollback

DROP INDEX idx_users_email;
DROP TABLE users;
```

## SQLite

### Connection URL

Add to your `warden.toml`:

```toml
database_type = "sqlite"

# File-based
sqlalchemy_url = "sqlite:///./mydb.db"

# In-memory
sqlalchemy_url = "sqlite:///:memory:"
```

No additional drivers needed.

### Features

- Simple file-based database
- Zero configuration
- Good for development/testing
- Full SQLite feature support

### Limitations

- No concurrent connections (file-based)
- Limited ALTER TABLE support
- Different type system (type affinity)

### Example SQLite Migration

```sql
-- upgrade

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- rollback

DROP TABLE users;
```

## ClickHouse

### Connection URL

Add to your `warden.toml`:

```toml
database_type = "clickhouse"
sqlalchemy_url = "clickhousedb+connect://default:@localhost:8123/analytics"
```

**Requirements:**

```bash
pip install clickhouse-connect
```

### Features

- Migration tracking tables use `ReplacingMergeTree`
- Supports `MergeTree`, `ReplacingMergeTree`, and other engines in user migrations
- Works with HTTP interface (default ClickHouse server configuration)

### Limitations

- ALTER TABLE DELETE/UPDATE statements run through ClickHouse mutations and may take extra time on large datasets
- Repeatable migrations perform delete-and-insert semantics to ensure idempotency
- Requires ClickHouse server version 24.8 or newer for consistent HTTP mutations

### Example ClickHouse Migration

```sql
-- upgrade

CREATE TABLE events (
    event_date Date DEFAULT today(),
    event_id UInt64,
    payload String
)
ENGINE = MergeTree()
ORDER BY (event_date, event_id);

-- rollback

DROP TABLE events;
```

### Modeling ClickHouse Tables with SQLAlchemy

When `database_type = "clickhouse"`, DBWarden reads ClickHouse-specific
metadata from:

- `__table_args__['info']` (or dictionaries nested inside `__table_args__`).
- `Column(..., info={...})` dictionaries.

Recognized keys include:

| Scope | Key | Description |
|-------|-----|-------------|
| Table | `clickhouse_engine` | Engine clause (e.g., `MergeTree()`). |
| Table | `clickhouse_order_by` | Expression for `ORDER BY`. |
| Table | `clickhouse_partition_by` | Partition expression. |
| Table | `clickhouse_primary_key` | Custom primary key tuple. |
| Table | `clickhouse_sample_by` | `SAMPLE BY` expression. |
| Table | `clickhouse_ttl` | Default TTL clause. |
| Table | `clickhouse_settings` | Dict/string of engine settings. |
| Column | `clickhouse_type` | Exact ClickHouse column type (overrides mapper). |
| Column | `clickhouse_codec` | `CODEC(...)` annotation. |
| Column | `clickhouse_ttl` | Column-level TTL expression. |

**Model Example**

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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
    occurred_at = Column(DateTime, nullable=False)
    payload = Column(String(255))
    is_active = Column(Boolean, nullable=False, default=True, info={"clickhouse_codec": "T64"})
```

During `make-migrations`, the generator converts SQLAlchemy types to ClickHouse
types (Integer→Int32, Boolean→UInt8, etc.) and applies the metadata shown above,
so the resulting SQL mirrors the ClickHouse expectations without manual edits.

## Connection Pooling

SQLAlchemy creates an engine with connection pool:

```python
from sqlalchemy import create_engine
engine = create_engine(url, pool_size=5, max_overflow=10)
```

## SSL/TLS Connections

### PostgreSQL with SSL

```toml
database_type = "postgres"
sqlalchemy_url = "postgresql://user:password@host:5432/db?sslmode=require"
```

### MySQL with SSL

```toml
database_type = "mysql"
sqlalchemy_url = "mysql://user:password@host:3306/db?ssl=true"
```

## Connection Strings Reference

### PostgreSQL

```
postgresql://user:pass@localhost:5432/mydb
postgresql://user:pass@host:5432/mydb?sslmode=require
postgresql://user:pass@host:5432/mydb?channel_binding=require
```

### MySQL

```
mysql://user:pass@localhost:3306/mydb
mysql+pymysql://user:pass@localhost:3306/mydb
mysql://user:pass@host:3306/mydb?ssl=true
```

### SQLite

```
sqlite:///./mydb.db
sqlite:///:memory:
sqlite:///path/to/file.db
```

### ClickHouse

```
clickhousedb+connect://default:@localhost:8123/analytics
clickhousedb+connect://user:pass@host:8123/db
```
