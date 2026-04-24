# Migration Locking

DBWarden uses migration locks to prevent concurrent schema mutation.

## Commands

```bash
dbwarden lock-status --database primary
dbwarden unlock --database primary
```

## Stale lock recovery

1. Confirm no migration process is running.
2. Check lock status.
3. Release lock with `unlock`.
4. Retry `migrate`.

## Navigation

- Previous: [SQL Translation](../sql-translation.md)
- Next: [Checksum Integrity](checksum-integrity.md)
