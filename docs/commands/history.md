# history Command

Display the complete migration history.

## Description

The `history` command shows a formatted table of all migrations that have been applied to the database, including their version, description, and when they were applied.

## Usage

```bash
dbwarden history
```

## Examples

### Basic Usage

```bash
$ dbwarden history
Migration History
================
Version | Order | Description     | Applied At           | Type
-------|-------|-----------------|----------------------|------
0001   | 1     | create users    | 2024-02-15 14:30:15 | versioned
0002   | 2     | create posts    | 2024-02-15 14:30:20 | versioned
0003   | 3     | add comments    | 2024-02-15 14:30:25 | versioned
```

### No Migrations Applied

```
No migrations have been applied yet.
```

## Output Columns

| Column | Description |
|--------|-------------|
| **Version** | Migration version identifier |
| **Order** | Sequence number of execution |
| **Description** | Migration description/name |
| **Applied At** | Timestamp when migration was applied |
| **Type** | Migration type (versioned) |

## What It Shows

- All successfully applied migrations
- Chronological order of application
- Execution sequence (order executed)
- Timestamps for each migration

## Use Cases

### Checking Applied Migrations

Verify which migrations are in the database:

```bash
dbwarden history
```

### Debugging Issues

When troubleshooting schema issues:

```bash
dbwarden history
# Check order and timing of migrations
```

### Auditing

For compliance and auditing:

```bash
dbwarden history > migration_audit_$(date +%Y%m%d).txt
```

## Related Commands

### Compare with Local Files

```bash
dbwarden history     # Database state
dbwarden status     # Compare with local files
```

### Check Pending Migrations

```bash
dbwarden history     # What's applied
dbwarden status     # Plus what's pending
```

## Database Source

The history is read from the `dbwarden_migrations` table in your database:

```sql
SELECT * FROM dbwarden_migrations ORDER BY applied_at;
```

## Troubleshooting

### "No migrations have been applied yet"

This means either:
1. No migrations have been run
2. The `dbwarden_migrations` table doesn't exist
3. Running `dbwarden migrate` for the first time

### Empty History Despite Migrations

If migrations were applied but history is empty:

1. Check you're connecting to the correct database
2. Verify `warden.toml` configuration
3. Check `dbwarden_migrations` table exists:

```bash
dbwarden check-db --out txt
# Look for dbwarden_migrations table
```

## Best Practices

1. **Regular checks**: Review history after deployments
2. **Documentation**: Note migration purposes in descriptions
3. **Retention**: Archive history for audit trails

## See Also

- [status](status.md): Show applied and pending migrations
- [migrate](migrate.md): Apply migrations
- [rollback](rollback.md): Revert migrations
