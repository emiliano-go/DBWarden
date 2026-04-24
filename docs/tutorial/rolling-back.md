# Rolling Back

Rollback executes the `-- rollback` section of applied migration files.

## What you'll learn

- how rollback selection works
- when to use `--count` vs `--to-version`
- how to recover safely when rollback fails

## Prerequisites

- applied migration history exists
- rollback SQL is defined in target migration files

## Run it

```bash
dbwarden rollback --database primary
dbwarden rollback --database primary --count 2
dbwarden rollback --database primary --to-version 0007
```

## What happened

- DBWarden loads applied migration history
- selects rollback candidates
- executes rollback SQL in reverse order
- updates migration metadata records

## Common failure modes

- rollback SQL doesn't match current schema state
- data rollback assumptions are invalid
- lock conflicts from concurrent migration process

When rollback is risky, prefer a forward-fix migration.

Reference: [Safe Deployment](../advanced/safe-deployment.md)

## Navigation

- Previous: [Applying Migrations](applying-migrations.md)
- Next: [Checking Status](checking-status.md)
