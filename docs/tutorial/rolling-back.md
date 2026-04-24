# Rolling Back

Rollback uses the `--rollback` SQL section from migration files.

Rollback is a first-class operation in DBWarden, not an afterthought.

## Roll back latest migration

```bash
dbwarden rollback --database primary
```

This defaults to one migration when `--count` and `--to-version` are omitted.

## Roll back multiple migrations

```bash
dbwarden rollback --database primary --count 2
```

## Roll back to a target version

```bash
dbwarden rollback --database primary --to-version 0007
```

Use `--to-version` when recovering to a known good checkpoint.

## How rollback is selected

DBWarden reads applied migration history, identifies rollback candidates, and executes rollback statements in reverse order.

## Best practices

- keep rollback SQL simple and deterministic
- avoid relying on unknown runtime state
- validate rollback path in pre-release testing
- prefer forward-fix migration when rollback would be riskier than correction

If rollback fails, inspect migration history and create a corrective forward migration.

Reference: [Safe Deployment](../advanced/safe-deployment.md)

## Navigation

- Previous: [Applying Migrations](applying-migrations.md)
- Next: [Checking Status](checking-status.md)
