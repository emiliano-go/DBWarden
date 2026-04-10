# Supported Databases

DBWarden supports multiple database backends. This guide covers configuration and considerations for each.

## Overview

| Database | Supported | Driver | Type Value |
|----------|-----------|--------|------------|
| PostgreSQL | Yes | `psycopg2-binary` | `postgresql` |
| MySQL | Yes | `mysql-connector-python` | `mysql` |
| SQLite | Yes | Built-in | `sqlite` |
| ClickHouse | Yes | `clickhouse-connect` | `clickhouse` |
| MariaDB | Yes | `mysql-connector-python` | `mariadb` |

## PostgreSQL

### Connection URL

```toml
[database.primary]
database_type = "postgresql"
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
- SERIAL/BIGSERIAL for auto-increment
- TIMESTAMP (not DATETIME)
- BYTEA for binary data

### PostgreSQL Schema

Set default schema in `warden.toml`:

```toml
[database.primary]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@localhost:5432/mydb"
postgres_schema = "custom_schema"
```

### Type Mapping

DBWarden automatically maps SQLAlchemy types to PostgreSQL:

| SQLAlchemy | PostgreSQL |
|------------|------------|
| Integer (PK) | SERIAL |
| BigInteger (PK) | BIGSERIAL |
| DateTime | TIMESTAMP |
| BLOB | BYTEA |

### Example PostgreSQL Migration

```sql
-- upgrade

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    data JSONB
);

CREATE INDEX idx_users_email ON users(email);

-- rollback

DROP INDEX idx_users_email;
DROP TABLE users;
```

## MySQL

### Connection URL

```toml
[database.legacy]
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

### Type Mapping

| SQLAlchemy | MySQL |
|------------|-------|
| Boolean | TINYINT(1) |
| Integer (PK) | INT AUTO_INCREMENT |

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

## MariaDB

MariaDB is fully compatible with MySQL. Use the `mariadb` type:

```toml
[database.legacy]
database_type = "mariadb"
sqlalchemy_url = "mysql://user:password@localhost:3306/mydb"
```

All MySQL features and type mappings apply to MariaDB.

## SQLite

### Connection URL

```toml
[database.dev]
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

```toml
[database.analytics]
database_type = "clickhouse"
sqlalchemy_url = "clickhouse://user:password@localhost:8123/analytics"
```

**Requirements:**
```bash
pip install clickhouse-connect
```

### Features

- Supports migration tracking and locking tables
- Supports model-generated and manual migrations
- Supports MergeTree/ReplacingMergeTree-style table migrations
- Excellent for analytics workloads
- Column-oriented storage

### Type Mapping

ClickHouse uses MySQL-compatible queries for migration tracking tables.

### Example ClickHouse Migration

```sql
-- upgrade

CREATE TABLE users (
    id UInt32,
    email String,
    created_at DateTime
) ENGINE = MergeTree()
ORDER BY id;

CREATE TABLE events (
    id UInt32,
    user_id UInt32,
    event_type String,
    created_at DateTime
) ENGINE = MergeTree()
ORDER BY (user_id, created_at);

-- rollback

DROP TABLE events;
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
[database.prod]
database_type = "postgresql"
sqlalchemy_url = "postgresql://user:password@host:5432/db?sslmode=require"
```

### MySQL with SSL

```toml
[database.prod]
database_type = "mysql"
sqlalchemy_url = "mysql://user:password@host:3306/db?ssl=true"
```

### ClickHouse with HTTPS

```toml
[database.analytics]
database_type = "clickhouse"
sqlalchemy_url = "clickhouse://user:password@host:8443/analytics?ssl=true"
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
clickhouse://user:pass@localhost:8123/analytics
clickhouse://user:pass@host:8123/db
clickhouse://user:pass@host:8443/db?ssl=true
```

### MariaDB

```
mariadb://user:pass@localhost:3306/mydb
mysql://user:pass@localhost:3306/mydb
```
