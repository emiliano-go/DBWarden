# Extended Statistics

**Handler**: `ExtendedStatisticsHandler` (PREAMBLE phase, config-driven, PG 14+)

Extended statistics give the query planner better estimates for correlated columns.

```python
pg_extended_statistics=[
    {
        "name": "stats_users_email_city",
        "table": "users",
        "kinds": ["d", "f"],
        "columns": "email, city",
    },
]
```

## Kind Codes

| Code | Kind | Description |
|------|------|-------------|
| `d` | ndistinct | Distinct-value counts for column groups |
| `f` | dependencies | Functional dependency statistics |
| `m` | MCV | Most-common-values lists |
| `e` | expressions | Expression statistics (PG 14+) |

## Lifecycle

| Operation | DDL |
|-----------|-----|
| Create | `CREATE STATISTICS name (kinds) ON columns FROM table;` |
| Drop | `DROP STATISTICS IF EXISTS name;` |

## Examples

```python
# ndistinct + dependencies on correlated columns
{"name": "stats_order_date_status", "table": "orders",
 "kinds": ["d", "f"], "columns": "order_date, status"}

# MCV on a high-cardinality group
{"name": "stats_product_category", "table": "products",
 "kinds": ["m"], "columns": "category_id, price"}

# Expression statistics (PG 14+)
{"name": "stats_user_email_domain", "table": "users",
 "kinds": ["d", "m"], "expressions": ["lower(email)"]}
```

Generated DDL:
```sql
CREATE STATISTICS stats_users_email_city (ndistinct, dependencies) ON email, city FROM users;
```
