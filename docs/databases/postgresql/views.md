# Views

**Handler**: `ViewHandler` (DIFF phase)

Views are model-derived via `PGViewMeta`.

## Regular Views

```python
from dbwarden.databases.pgsql import PGViewMeta

class ActiveUser(Base):
    __tablename__ = "active_users"

    id: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String(255))

    class Meta(PGViewMeta):
        pg_view_query = "SELECT id, email, name FROM users WHERE active = true"
        pg_view_materialized = False
```

Generated DDL:
```sql
CREATE OR REPLACE VIEW active_users AS SELECT id, email, name FROM users WHERE active = true;
```

## Materialized Views

```python
class OrderSummary(Base):
    __tablename__ = "order_summary"

    user_id: Mapped[int] = mapped_column(Integer)
    total: Mapped[float] = mapped_column(Integer)

    class Meta(PGViewMeta):
        pg_view_query = "SELECT user_id, count(*) AS total FROM orders GROUP BY user_id"
        pg_view_materialized = True
```

Generated DDL:
```sql
CREATE MATERIALIZED VIEW order_summary AS SELECT user_id, count(*) AS total FROM orders GROUP BY user_id;
```

## Auto-Refresh

Set `pg_view_auto_refresh = True` to emit `REFRESH MATERIALIZED VIEW` in subsequent migrations:

```python
class Meta(PGViewMeta):
    pg_view_query = "..."
    pg_view_materialized = True
    pg_view_auto_refresh = True
```

```sql
REFRESH MATERIALIZED VIEW order_summary;
```

## Schema-Qualified Views

```python
class Meta(PGViewMeta):
    pg_view_query = "SELECT id, email FROM users"
    pg_view_materialized = False
    pg_schema = "app"
```

```sql
CREATE OR REPLACE VIEW app.active_users AS SELECT id, email FROM users;
```

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create regular view | `CREATE OR REPLACE VIEW name AS query;` |
| Create matview | `CREATE MATERIALIZED VIEW name AS query;` |
| Refresh matview | `REFRESH MATERIALIZED VIEW name;` |
| Drop | `DROP VIEW IF EXISTS name CASCADE;` / `DROP MATERIALIZED VIEW IF EXISTS name CASCADE;` |
