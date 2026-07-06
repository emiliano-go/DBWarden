# RLS & Policies

**Handler**: `PoliciesHandler` (DIFF phase)

Row-Level Security and policies are model-derived, declared on `PGTableMeta`.

## Enabling RLS

```python
class Meta(PGTableMeta):
    pg_rls = True
```

Generated DDL:
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### FORCE / NO FORCE

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_rls_force = True
```

Generated DDL:
```sql
ALTER TABLE users FORCE ROW LEVEL SECURITY;
```

To disable force (without disabling RLS):

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_rls_force = False
```

```sql
ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
```

The force flag only emits when it explicitly changes. If `pg_rls_force` is absent or `False` on both the snapshot and model sides, no `FORCE`/`NO FORCE` DDL is generated. This avoids churn on indexes that only toggle RLS without changing force.

## Policies

Policies are declared as a list on `PGTableMeta`:

```python
class Meta(PGTableMeta):
    pg_rls = True
    pg_policies = [
        {
            "name": "tenant_isolation",
            "using": "tenant_id = current_setting('app.tenant_id')::int",
            "roles": ["app_user"],
            "permissive": True,
        },
    ]
```

### Policy Keys

| Key | Description |
|-----|-------------|
| `name` | Policy name |
| `using` | `USING` expression (row visibility) |
| `with_check` | `WITH CHECK` expression (row modification) |
| `roles` | Roles the policy applies to (absent = all roles) |
| `permissive` | `PERMISSIVE` (default) or `RESTRICTIVE` |
| `command` | `ALL` (default), `SELECT`, `INSERT`, `UPDATE`, `DELETE` |

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Add policy | `CREATE POLICY name ON table FOR command USING (expr)` |
| Alter policy | `ALTER POLICY name ON table USING (new_expr)` |
| Drop policy | `DROP POLICY IF EXISTS name ON table` |
| Enable RLS | `ALTER TABLE table ENABLE ROW LEVEL SECURITY` |
| Disable RLS | `ALTER TABLE table DISABLE ROW LEVEL SECURITY` |
| Force RLS | `ALTER TABLE table FORCE ROW LEVEL SECURITY` |
| Remove force | `ALTER TABLE table NO FORCE ROW LEVEL SECURITY` |
