# Squashing Migrations

Squashing consolidates multiple migrations into a smaller set after a stable release boundary.

## Command

```bash
dbwarden squash --database primary
```

Use squashing only when:

- no pending migrations remain
- your team agrees on a stable checkpoint
- rollback strategy remains clear

## When to squash

After multiple versioned migrations that have been stable through several releases, you may want to consolidate them to reduce file count and simplify rollback.

## Workflow recommendation

1. Confirm all migrations are applied and stable
2. Run squash and review new consolidated file
3. Test that rollback still works correctly
4. Keep the new file, retire the old ones in version control

## Navigation

- Previous: [Checksum Integrity](checksum-integrity.md)
- Next: [CI/CD Patterns](ci-cd-patterns.md)