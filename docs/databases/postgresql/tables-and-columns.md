# Tables & Columns

**Handlers**: `TableHandler`, `ColumnHandler` (DIFF phase)

## Table Lifecycle

| Operation | DDL |
|-----------|-----|
| Create table | `CREATE TABLE name (...)` |
| Drop table | `DROP TABLE IF EXISTS name CASCADE;` |
| Alter table comment | `COMMENT ON TABLE name IS 'comment';` |

## Column Lifecycle

| Operation | DDL |
|-----------|-----|
| Add column | `ALTER TABLE t ADD COLUMN c type;` |
| Drop column | `ALTER TABLE t DROP COLUMN c;` |
| Change type | `ALTER TABLE t ALTER COLUMN c TYPE newtype;` |
| Change nullable | `ALTER TABLE t ALTER COLUMN c SET/DROP NOT NULL;` |
| Change default | `ALTER TABLE t ALTER COLUMN c SET/DROP DEFAULT;` |
| Change comment | `COMMENT ON COLUMN t.c IS 'comment';` |
| Change autoincrement | `CREATE/DROP SEQUENCE` + `SET/DROP DEFAULT nextval` |
| Change PG meta | `SET STORAGE`, `SET COMPRESSION`, `SET COLLATION`, identity options |
| Rename column | `ALTER TABLE t RENAME COLUMN c TO new_name;` |

## Table Properties

| Property | Meta Attribute | DDL |
|----------|---------------|-----|
| Fillfactor | `pg_fillfactor` | `ALTER TABLE t SET (fillfactor = N);` |
| Tablespace | `pg_tablespace` | `ALTER TABLE t SET TABLESPACE name;` |
| Unlogged | `pg_unlogged` | `CREATE UNLOGGED TABLE` / `ALTER TABLE t SET UNLOGGED;` |
| Inheritance | `pg_inherits` | `ALTER TABLE t INHERIT parent;` |
| Storage params | (via handler) | `ALTER TABLE t SET (param = value);` |

## Snapshot Format

### Column Extras

```json
{
  "name": "bio",
  "type": "text",
  "pg_column": {
    "collation": "en_US.UTF-8",
    "storage": "EXTENDED",
    "compression": "pglz",
    "generated": null,
    "identity": "always",
    "identity_start": 1,
    "identity_increment": 1
  }
}
```

### Table Extras

```json
{
  "pg_table": {
    "pg_fillfactor": 80,
    "pg_tablespace": "fastspace",
    "pg_unlogged": false,
    "pg_inherits": "base_entity",
    "pg_partition": {
      "strategy": "RANGE",
      "columns": ["created_at"]
    },
    "pg_excludes": [
      {"name": "excl_room_booking", "expression": "EXCLUDE USING gist (room_id WITH =, during WITH &&)"}
    ]
  }
}
```

## Reverse Engineering

`generate-models` queries `pg_class`, `pg_attribute`, `pg_constraint`, `pg_inherits`, `pg_tablespace`, `pg_partitioned_table`, and `pg_collation` to reverse-engineer all metadata.

```bash
$ dbwarden generate-models -d primary
```

Generated output for a table with identity, storage, compression, collation, and fillfactor:

```python
class User(Base):
    __tablename__ = "users"

    id:    Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    bio:   Mapped[str | None] = mapped_column(Text, nullable=True)

    class Meta(PGTableMeta):
        comment = "Core user accounts"
        pg_fillfactor = 80

        class id(PGColumnMeta):
            pg = pg.field(identity="always", identity_start=100, identity_increment=1)

        class bio(PGColumnMeta):
            pg = pg.field(storage="EXTENDED", compression="pglz", collation="en_US.UTF-8")
```

For a partitioned table:

```python
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    class Meta(PGTableMeta):
        pg_partition = {"strategy": "RANGE", "columns": ["created_at"]}
```
