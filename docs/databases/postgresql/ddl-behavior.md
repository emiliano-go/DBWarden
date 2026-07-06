# DDL Behavior

## Transactional DDL

PostgreSQL DDL is transactional. If a migration file contains multiple statements and one fails, all prior DDL in that file is rolled back. This makes PostgreSQL the safest backend for automated migration runs.

## Index Creation

DBWarden defaults to `CREATE INDEX CONCURRENTLY` to avoid table locking. Pass `--no-concurrent` when the migration must run inside a transaction block (PostgreSQL requires `CONCURRENTLY` outside a transaction).

## Column Type Changes

Emits `ALTER TABLE t ALTER COLUMN c TYPE newtype` with a commented-out `-- USING col::newtype` line. Pass `--postgres-auto-using` to emit an active `USING` clause. Without the flag, uncomment and verify the USING expression before running the migration against production.

### Safe Type Change

The `--safe-type-change` flag generates a multi-step strategy:
1. Add a temporary column with the new type
2. Emit a `--` comment with an `UPDATE` statement template
3. Emit a verification comment
4. After manual verification, drop the old column and rename the temporary column

## Generated Columns

Adding a generated column via `ALTER TABLE` is not supported by PostgreSQL. DBWarden emits a comment placeholder noting this limitation. Dropping the generation expression (`ALTER COLUMN c DROP EXPRESSION`) produces real DDL.

## Auto-increment Lifecycle

DBWarden supports toggling auto-increment on integer primary key columns:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    class Meta(PGTableMeta):
        id = ColumnMeta(autoincrement=True)
```

To explicitly disable auto-increment:

```python
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
```

| Change | Generated SQL |
|--------|---------------|
| Adding autoincrement | `CREATE SEQUENCE users_id_seq` + `ALTER COLUMN id SET DEFAULT nextval(...)` + `ALTER SEQUENCE ... OWNED BY` |
| Removing autoincrement | `ALTER COLUMN id DROP DEFAULT` + `DROP SEQUENCE IF EXISTS users_id_seq` |

### Detection from live databases

DBWarden detects autoincrement by:
1. SERIAL/BIGSERIAL column types
2. SQLAlchemy's `.autoincrement` attribute
3. `nextval(...)` default patterns

### Type mapping

| Condition | Resulting Type |
|-----------|---------------|
| `autoincrement=True` (default) | `SERIAL` / `BIGSERIAL` |
| `autoincrement=False` | `INTEGER` / `BIGINT` |
| `autoincrement=None` (unspecified) | `SERIAL` / `BIGSERIAL` (backward compatible) |
