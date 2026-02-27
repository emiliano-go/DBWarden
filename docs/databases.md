# Supported Databases

DBWarden supports multiple database backends. This guide covers configuration and considerations for each.

## Overview

| Database | Supported | Driver Required |
|----------|-----------|-----------------|
| PostgreSQL | Yes | `psycopg2-binary` |
| MySQL | Yes | `mysql-connector-python` |
| SQLite | Yes | Built-in |

## PostgreSQL

### Connection URL

Add to your `warden.toml`:

```toml
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

## Connection Pooling

SQLAlchemy creates an engine with connection pool:

```python
from sqlalchemy import create_engine
engine = create_engine(url, pool_size=5, max_overflow=10)
```

## SSL/TLS Connections

### PostgreSQL with SSL

```toml
sqlalchemy_url = "postgresql://user:password@host:5432/db?sslmode=require"
```

### MySQL with SSL

```toml
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
