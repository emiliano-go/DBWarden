# Grants & Roles

Grants are handled by `GrantsHandler` (DIFF phase). Roles are handled by `RoleHandler` (PREAMBLE phase). Default privileges are handled by `DefaultPrivilegesHandler` (PREAMBLE phase).

## Table Grants

Grants are model-derived, declared per-table on the model.

### Grant Types

| Operation | DDL |
|-----------|-----|
| Grant | `GRANT privileges ON TABLE table TO role;` |
| Revoke | `REVOKE privileges ON TABLE table FROM role;` |

Supported privileges: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `TRIGGER`, `ALL`.

## Schema Grants

Schema grants use the same `GrantsHandler` with `object_type="schema"`:

| Operation | DDL |
|-----------|-----|
| Grant | `GRANT USAGE ON SCHEMA schema TO role;` |
| Revoke | `REVOKE USAGE ON SCHEMA schema FROM role;` |

## Roles

**Handler**: `RoleHandler` (PREAMBLE phase, config-driven)

```python
pg_roles=[
    {"name": "app_user", "login": True, "password": "encrypted"},
    {"name": "readonly", "login": True, "connection_limit": 5},
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE ROLE name WITH options` |
| Alter | `ALTER ROLE name WITH options` |
| Drop | `DROP ROLE IF EXISTS name` |

Roles are filtered to non-bootstrap roles (excludes `pg_*` roles and default cluster roles).

## Default Privileges

**Handler**: `DefaultPrivilegesHandler` (PREAMBLE phase, config-driven)

```python
pg_default_privileges=[
    {
        "schema": "public",
        "role": "app_user",
        "kind": "TABLES",
        "privileges": "SELECT, INSERT, UPDATE, DELETE",
    },
]
```

### Lifecycle

| Operation | DDL |
|-----------|-----|
| Grant | `ALTER DEFAULT PRIVILEGES FOR ROLE role IN SCHEMA schema GRANT privileges ON kind TO role;` |
| Revoke | `ALTER DEFAULT PRIVILEGES FOR ROLE role IN SCHEMA schema REVOKE privileges ON kind FROM role;` |

### Object Kinds

| Kind | Objects Covered |
|------|----------------|
| `TABLES` | Tables, views, materialized views |
| `SEQUENCES` | Sequences |
| `FUNCTIONS` | Functions, procedures |
| `TYPES` | Types, domains |
| `SCHEMAS` | Schemas |
