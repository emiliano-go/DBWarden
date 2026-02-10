# check-db Command

Inspect and display the live database schema.

## Description

The `check-db` command connects to your database and displays information about its current schema, including tables, columns, indexes, and foreign keys.

## Usage

```bash
dbwarden check-db [OPTIONS]
```

## Options

| Short | Long | Description |
|-------|------|-------------|
| `-o` | `--out FORMAT` | Output format: `txt` (default), `json`, `yaml`, `sql` |

**This option is not required. Default is `txt`.**

## Examples

### Text Output (Default)

```bash
dbwarden check-db
# or
dbwarden check-db --out txt
```

### JSON Output

```bash
dbwarden check-db --out json
# or
dbwarden check-db -o json
```

### YAML Output

```bash
$ dbwarden check-db --out yaml
users:
  columns:
  - {default: null, name: id, nullable: false, type: INTEGER}
  - {default: null, name: username, nullable: false, type: VARCHAR(50)}
  foreign_keys: []
  indexes:
  - {columns: [email], name: idx_users_email}
```

### SQL Output

```bash
$ dbwarden check-db --out sql
-- Table: users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME
);

-- Table: posts
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT
);
```

### SQL Output

```bash
dbwarden check-db --out sql
# or
dbwarden check-db -o sql
```

## What It Inspects

### Tables

- All tables in the database
- Tables in specific PostgreSQL schema (if `DBWARDEN_POSTGRES_SCHEMA` is set)

### Columns

For each table, displays:
- Column name
- Data type
- Nullable status
- Default value

### Indexes

- Index name
- Indexed columns
- Index type (if available)

### Foreign Keys

- Constraint name
- Local columns
- Referenced table
- Referenced columns

## Use Cases

### Documentation

Generate schema documentation:

```bash
dbwarden check-db --out yaml > schema.yaml
```

### Debugging

Compare expected vs actual schema:

```bash
# Your expected schema from models
# vs actual database schema
dbwarden check-db
```

### Integration

Use in scripts with JSON output:

```bash
SCHEMA=$(dbwarden check-db --out json)
# Process with jq or other tools
echo "$SCHEMA" | jq '.users.columns | length'
```

### Migration Verification

Before and after migration checks:

```bash
# Before
dbwarden check-db > before.json

# Apply migration
dbwarden migrate

# After
dbwarden check-db > after.json

# Compare
diff before.json after.json
```

## Technical Details

### Connection Used

Uses the same database connection as other commands:
- Reads from `warden.toml` configuration
- Uses `sqlalchemy_url`
- Respects `async` setting

### Schema Inspection

Uses SQLAlchemy's `inspect` function:
```python
from sqlalchemy import inspect
inspector = inspect(connection)
tables = inspector.get_table_names()
```

## Troubleshooting

### Connection Failed

Verify database connection:

```bash
dbwarden env
# Check sqlalchemy_url is correct

# Test connection
python -c "from sqlalchemy import create_engine; engine = create_engine('$URL'); engine.connect()"
```

### Empty Output

No tables found:
1. Check migrations were applied: `dbwarden history`
2. Verify correct database: Check connection URL
3. Check PostgreSQL schema: Set `postgres_schema` in warden.toml

## Best Practices

1. **Use before migrations**: Document current state
2. **Use after migrations**: Verify changes
3. **Version control schema**: Store `check-db` output in docs
4. **JSON for automation**: Use JSON format in scripts

## See Also

- [diff](diff.md): Compare models vs database
- [history](history.md): View migration history
- [status](status.md): Check migration status
