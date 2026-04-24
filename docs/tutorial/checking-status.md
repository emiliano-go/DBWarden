# Checking Status

Use `status`, `history`, and `check-db` to understand migration state before and after changes.

## What you'll learn

- when to run status commands
- how to read applied vs pending signals
- how to inspect live schema quickly

## Prerequisites

- project initialized with DBWarden
- at least one configured database

## Run it

```bash
dbwarden status --database primary
dbwarden history --database primary
dbwarden check-db --database primary
```

For multi-database projects:

```bash
dbwarden status --all
```

## What happened

- `status` reports applied and pending migration counts
- `history` reports execution records and order
- `check-db` reports current database schema details

## Recommended operational loop

```bash
dbwarden status --database primary
dbwarden migrate --database primary
dbwarden status --database primary
dbwarden history --database primary
```

## Common failure modes

- database name typo in `--database`
- migration files missing from expected migrations directory
- lock conflicts from concurrent migration runners

Reference: [CLI Reference](../cli-reference.md)

## Navigation

- Previous: [Rolling Back](rolling-back.md)
- Next: [Dev Mode](dev-mode.md)
