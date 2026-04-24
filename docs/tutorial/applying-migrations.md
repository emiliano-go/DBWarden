# Applying Migrations

Use `migrate` to apply pending migrations safely.

## What you'll learn

- how DBWarden executes migration plans
- when to use `--all`, `--count`, `--to-version`, and `--baseline`
- how to verify migration outcomes

## Prerequisites

- generated migration files exist
- target database is configured and reachable

## Run it

```bash
dbwarden migrate --database primary
```

Other common forms:

```bash
dbwarden migrate --all
dbwarden migrate --database primary --count 2
dbwarden migrate --database primary --to-version 0010
dbwarden migrate --database primary --baseline --to-version 0005
dbwarden migrate --database primary --with-backup --backup-dir ./backups
```

## What happened

At runtime DBWarden:

1. resolves target database config
2. ensures metadata and lock tables exist
3. computes pending migration plan
4. acquires lock and executes SQL
5. records migration metadata/checksums
6. releases lock

## Verify it

```bash
dbwarden status --database primary
dbwarden history --database primary
```

## Common failure modes

- lock conflicts from concurrent migration process
- invalid SQL in migration file
- unsupported translation behavior in `--dev` mode

Reference: [CLI Reference](../cli-reference.md)

## Navigation

- Previous: [Your First Migration](your-first-migration.md)
- Next: [Rolling Back](rolling-back.md)
