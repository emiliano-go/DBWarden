# SQLAlchemy Models

DBWarden can generate migration SQL from SQLAlchemy model definitions.

This page explains both usage and internal extraction behavior.

## Minimum Requirements

Each model should:

1. Be a class with `__tablename__`
2. Expose `__table__` columns through SQLAlchemy declarative mapping
3. Use supported SQLAlchemy column types

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
```

## Model Discovery Internals

`make-migrations` discovers models from configured `model_paths` or auto-discovered `models/` folders.

High-level process:

```python
def discover_tables(paths):
    modules = load_python_modules(paths)
    tables = []
    seen = set()
    for module in modules:
        for attr in module_attributes(module):
            if is_sqlalchemy_model(attr) and attr.__tablename__ not in seen:
                tables.append(extract_table(attr))
                seen.add(attr.__tablename__)
    return tables
```

Duplicate table names are skipped after first discovery.

## Column Extraction Internals

For each SQLAlchemy `Column`, DBWarden extracts:

- name
- type string
- nullability
- primary key flag
- unique flag
- default expression
- foreign key reference

For SQLite dev mode, DBWarden runs translation on extracted type/default fields.

## Common Model Patterns

## Typical App Models

```python
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base
import datetime as dt

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text)
```

## Composite Key Example

```python
class OrderItem(Base):
    __tablename__ = "order_items"

    order_id = Column(Integer, ForeignKey("orders.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, nullable=False)
```

## JSON + UUID Style Example

```python
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settings = Column(JSON, default=dict)
```

In SQLite dev mode these may translate (for example `UUID` and `JSON` to `TEXT`).

## Type Behavior by Backend

DBWarden maps SQLAlchemy-like types to backend-specific SQL during generation.

- PostgreSQL: supports `SERIAL`, `TIMESTAMP`, `BYTEA`
- MySQL/MariaDB: maps booleans to compatible types
- SQLite: simple type affinity model
- Dev translation: can adapt non-SQLite types when running `--dev` with SQLite

For translation specifics, see [SQL Translation](sql-translation.md).

## Practical Guidelines

- Keep model imports side-effect free (module import should not run app boot logic)
- Prefer explicit nullability and defaults
- Use manual migrations for backend-specific advanced objects (indexes, triggers, policies)
- Review generated SQL before applying

## Troubleshooting

No models found:

- Ensure `model_paths` points to real files/directories
- Ensure classes define `__tablename__`
- Ensure SQLAlchemy models are importable in current environment

Wrong SQL type output:

- Check selected database config
- If running `--dev`, check `dev_database_url` and translation behavior
- Use `--strict-translation` to surface lossy conversion failures early
