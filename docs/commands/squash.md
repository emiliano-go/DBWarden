# `squash`

Consolidate multiple migrations into a smaller set after a stable release boundary.

## Usage

```bash
dbwarden squash --database primary
```

## Options

- `--database`, `-d`
- `--verbose`, `-v`

## When to squash

Use squashing only when:

- no pending migrations remain
- your team agrees on a stable checkpoint
- rollback strategy remains clear

After multiple versioned migrations that have been stable through several releases, you may want to consolidate them to reduce file count and simplify rollback.

## Workflow recommendation

1. Confirm all migrations are applied and stable
2. Run squash and review new consolidated file
3. Test that rollback still works correctly
4. Keep the new file, retire the old ones in version control

## Notes

- use after stable release boundaries
- ensure no pending migrations before squashing
