# Constraints

Constraints are handled by `ConstraintHandler` during the DIFF phase.

## Foreign Keys

FK comparison uses a signature tuple: `(columns, ref_table, ref_columns, on_delete, on_update, deferrable, match)`.

### MATCH Behaviour

PostgreSQL supports three FK match modes: `MATCH FULL`, `MATCH PARTIAL`, and `MATCH SIMPLE` (default).

- `MATCH FULL` is explicitly emitted in DDL
- `MATCH PARTIAL` is explicitly emitted
- `MATCH SIMPLE` and absent match are canonicalized to the same representation (no match clause) to avoid churn on existing FKs

```sql
ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (ref_id) REFERENCES ref (id) MATCH FULL;
ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (ref_id) REFERENCES ref (id) ON DELETE CASCADE;
```

### ON DELETE / ON UPDATE

Supported actions: `CASCADE`, `SET NULL`, `SET DEFAULT`, `RESTRICT`, `NO ACTION`.

### DEFERRABLE

Support for `DEFERRABLE` / `NOT DEFERRABLE` and `INITIALLY DEFERRED` / `INITIALLY IMMEDIATE`.

### NOT VALID / VALIDATE

FKs can be created `NOT VALID` and validated later with `VALIDATE CONSTRAINT`.

## Unique Constraints

Support for:

- `DEFERRABLE` / `INITIALLY DEFERRED`
- `INCLUDE` columns
- `NULLS NOT DISTINCT` (PG 15+)

## Check Constraints

Support for:

- Arbitrary CHECK expressions
- `NO INHERIT` (constraint not applied to child tables)
- `NOT VALID` + `VALIDATE`

## Exclude Constraints

Declared via `pg_excludes` on `PGTableMeta`. Uses `PgTableHandler`.

```python
class Meta(PGTableMeta):
    pg_excludes = [
        {"name": "excl_room_booking", "expression": "USING gist (room_id WITH =, during WITH &&)"},
    ]
```

## Constraint Diffing

Constraints are compared by full attribute content. Any difference in signature (columns, expression, options) produces `DROP` + `ADD`. Constraint name changes are detected as a new constraint.
