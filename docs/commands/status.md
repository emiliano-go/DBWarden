# status Command

Display the current migration status including applied and pending migrations.

## Description

The `status` command shows a comprehensive view of your migration state, comparing migration files in the local directory with what has been applied to the database.

## Usage

```bash
dbwarden status
```

## Examples

### Basic Usage

```
Migration Status
================
✓ Applied   | 0001_create_users
✓ Applied   | 0002_create_posts
✓ Applied   | 0003_add_comments
Pending     | 0004_add_tags

Applied: 3
Pending: 1
Total: 4
```

### No Migrations Directory

```
migrations directory not found. Run 'dbwarden init' first.
```

### No Migrations Applied Yet

```
Migration Status
================
Status    | Version | Filename
Pending   | 0001    | 0001_initial.sql

Applied: 0
Pending: 1
Total: 1
```

## Output Columns

| Column | Description |
|--------|-------------|
| **Status** | Migration state (Applied/Pending) |
| **Version** | Migration version identifier |
| **Filename** | Migration file name |

## Status Types

| Status | Icon | Meaning |
|--------|------|---------|
| Applied | ✓ | Successfully applied to database |
| Pending | (none) | Not yet applied to database |

## Use Cases

### Before Applying Migrations

Check what's pending before deployment:

```bash
dbwarden status
# Review pending migrations
dbwarden migrate
```

### After Deployment

Verify all migrations were applied:

```bash
dbwarden status
# Confirm Applied count matches expectations
```

### Debugging Issues

When schema doesn't match expectations:

```bash
dbwarden status
# Check which migrations are pending
dbwarden migrate
# Apply any missing migrations
```

## Comparing with History

| Command | Shows | Source |
|---------|-------|--------|
| `status` | Applied + Pending | Local files + Database |
| `history` | Applied only | Database only |

## Summary Statistics

The status command provides counts:

```
Applied: 3     # Migrations in database
Pending: 1     # Migrations not yet applied
Total: 4       # All migration files
```

## Troubleshooting

### Pending Migrations Exist

If pending migrations are shown:

```bash
dbwarden migrate --verbose
```

### Applied Count Doesn't Match

If applied count is unexpected:

1. Check `dbwarden history` for applied migrations
2. Verify database connection in `warden.toml`
3. Check for migrations in wrong location

### No Migrations Directory

Run initialization:

```bash
dbwarden init
```

## Workflow Integration

### Development Workflow

```bash
# 1. Check current state
dbwarden status

# 2. Make model changes
# ... edit models ...

# 3. Generate migration
dbwarden make-migrations "describe changes"

# 4. Check status
dbwarden status

# 5. Apply migration
dbwarden migrate
```

### Deployment Workflow

```bash
# 1. Check status before deployment
dbwarden status

# 2. Apply pending migrations
dbwarden migrate --verbose

# 3. Verify deployment
dbwarden status
```

## Best Practices

1. **Always check status** before applying migrations
2. **Review pending** migrations in detail
3. **Compare counts** before and after operations
4. **Document discrepancies** if any found

## See Also

- [history](history.md): Show applied migrations only
- [migrate](migrate.md): Apply pending migrations
- [make-migrations](make-migrations.md): Generate new migrations
