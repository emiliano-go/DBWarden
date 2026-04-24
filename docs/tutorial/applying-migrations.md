# Applying Migrations

Use `migrate` to apply pending migrations safely.

## What `migrate` does

At runtime, DBWarden:

1. resolves target database config
2. creates metadata/lock tables when missing
3. computes pending plan (versioned + repeatables)
4. acquires migration lock
5. executes SQL and records migration metadata
6. releases lock and prints summary

## Apply one database

```bash
dbwarden migrate --database primary
```

Use this in most production deployments where one database is owned by one service.

## Apply all configured databases

```bash
dbwarden migrate --all
```

DBWarden runs configured databases sequentially.

## Baseline workflow

If a database already has schema state and you need DBWarden to start tracking from a version without replaying old SQL:

```bash
dbwarden migrate --database primary --baseline --to-version 0005
```

Use this carefully and only when schema parity has been verified.

## Useful options

- `--to-version <version>`: stop at a specific version
- `--count <n>`: apply only the next N migrations
- `--with-backup`: create a backup before migrate
- `--baseline --to-version <version>`: mark historical versions as applied

## Verify after apply

```bash
dbwarden status --database primary
dbwarden history --database primary
```

You should see pending versions decrease and new records appear in history.

## Failure handling

If migration fails:

1. run `status` and `history` to inspect state
2. check lock state with `lock-status`
3. fix SQL/environment issue
4. re-run `migrate` or rollback intentionally

Reference: [CLI Reference](../cli-reference.md)

## Navigation

- Previous: [Your First Migration](your-first-migration.md)
- Next: [Rolling Back](rolling-back.md)
