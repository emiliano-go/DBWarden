# new Command

Create a new manual migration file.

## Description

The `new` command creates a blank migration file for manual SQL authoring. Use this when you need to write custom SQL that cannot be auto-generated from models.

## Usage

```bash
dbwarden new DESCRIPTION [OPTIONS]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `description` | **Required** - A descriptive name for the migration |

## Options

| Short | Long | Description |
|-------|------|-------------|
| | `--version VERSION` | Specific version number for the migration |

**Note: The `--version` option does not have a short form. Use `--version` or `--version VERSION`.**

## Examples

### Basic Usage

```bash
dbwarden new "add index to users email"
```

### With Custom Version

```bash
dbwarden new "migrate data from old schema" --version 9999
```

## Generated File Structure

```sql
-- migrations/0005_add_index_to_users_email.sql

-- upgrade

-- add index to users email

-- rollback

-- add index to users email
```

## Migration Headers

### Dependencies

Specify dependencies on other migrations:

```sql
-- depends_on: ["0001", "0002"]

-- upgrade

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(200) NOT NULL
);

-- rollback

DROP TABLE posts;
```

DBWarden will execute migrations in dependency order.

### Seed Migrations

Mark migrations as seed data (runs after all versioned migrations):

```sql
-- seed

-- upgrade

INSERT INTO service_types (name, kind) VALUES
('Web Service', 'api'),
('Database', 'db'),
('Cache', 'cache');

-- rollback

DELETE FROM service_types WHERE name IN ('Web Service', 'Database', 'Cache');
```

Seed migrations are useful for:
- Reference data
- Lookup tables
- Configuration data

## When to Use Manual Migrations

Use `new` instead of `make-migrations` when you need to:

- **Add indexes**: Performance optimizations
- **Add constraints**: Advanced constraints not in models
- **Custom data migrations**: Transform or clean existing data
- **Database-specific features**: Use features specific to your database
- **Complex alterations**: Modify multiple tables atomically

## Example: Adding an Index

```sql
-- migrations/0005_add_users_email_index.sql

-- upgrade

CREATE INDEX idx_users_email ON users(email);

-- rollback

DROP INDEX idx_users_email;
```

## Example: Data Migration

```sql
-- migrations/0006_normalize_usernames.sql

-- upgrade

UPDATE users
SET username = LOWER(username)
WHERE username IS NOT NULL;

-- rollback

-- No rollback needed for data normalization
```

## Example: Complex Schema Change

```sql
-- migrations/0007_add_post_status.sql

-- upgrade

ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'draft';

CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');

ALTER TABLE posts DROP COLUMN status;
ALTER TABLE posts ADD COLUMN status post_status DEFAULT 'draft';

-- rollback

DROP TYPE post_status;
ALTER TABLE posts DROP COLUMN status;
ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'draft';
```

## Version Numbering

If you don't specify a version, the next sequential number is auto-generated:

```
0001_initial_schema.sql
0002_add_users.sql
0003_add_posts.sql
0004_breaking_changes.sql
```

Custom versions must be 4-digit numbers:

```bash
dbwarden new "urgent fix" --version 9999
```

## Example: Data Migration

```sql
-- migrations/0003_normalize_usernames.sql

-- upgrade

UPDATE users
SET username = LOWER(username)
WHERE username IS NOT NULL;

-- rollback

-- No rollback needed for data normalization
```

## Example: Complex Schema Change

```sql
-- migrations/0004_add_post_status.sql

-- upgrade

ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'draft';

CREATE TYPE post_status AS ENUM ('draft', 'published', 'archived');

ALTER TABLE posts DROP COLUMN status;
ALTER TABLE posts ADD COLUMN status post_status DEFAULT 'draft';

-- rollback

DROP TYPE post_status;
ALTER TABLE posts DROP COLUMN status;
ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'draft';
```

## Version Numbering

If you don't specify a version, the next sequential number is auto-generated:

```
0001_initial.sql
0002_add_users.sql
0003_add_posts.sql
0004_breaking_changes.sql
```

Custom versions must be 4-digit numbers:

```
0001_initial.sql
0002_add_users.sql
0003_add_posts.sql
9999_urgent_fix.sql
```

## Best Practices

1. **Descriptive names**: Include what the migration does:
   ```
   0005_add_users_email_index.sql
   # NOT
   0005_index.sql
   ```

2. **Test rollback SQL**: Ensure `-- rollback` section works correctly

3. **Idempotent migrations**: Write SQL that can be run multiple times safely

4. **Document complex migrations**: Add comments explaining complex operations

5. **Separate concerns**: One migration per logical change

## Comparison: make-migrations vs new

| Aspect | make-migrations | new |
|--------|-----------------|-----|
| **Source** | SQLAlchemy models | Manual |
| **Use Case** | Schema from models | Custom SQL |
| **Automation** | Full | None |
| **Complexity** | Simple | Complex |
| **Risk** | Lower | Higher |

## Tips for Writing Manual Migrations

### 1. Always Include Rollback

```sql
-- GOOD
CREATE INDEX idx_users_email ON users(email);
-- rollback
DROP INDEX idx_users_email;

-- BAD (no rollback)
CREATE INDEX idx_users_email ON users(email);
```

### 2. Use Transactions When Possible

```sql
-- upgrade
BEGIN;
-- your SQL here
COMMIT;
```

### 3. Handle Existing Data

```sql
-- upgrade
ALTER TABLE users ADD COLUMN new_field VARCHAR(100);

UPDATE users SET new_field = 'default' WHERE new_field IS NULL;

ALTER TABLE users ALTER COLUMN new_field SET NOT NULL;
```

## Troubleshooting

### Version Already Exists

```
Error: Migration version already exists.
```

Use a different version or description.

### Empty Migration

Ensure you write SQL in both `-- upgrade` and `-- rollback` sections.

## See Also

- [make-migrations](make-migrations.md): Auto-generate from models
- [migrate](migrate.md): Apply manual migrations
- [Migration Files](../migration-files.md): Migration file format
