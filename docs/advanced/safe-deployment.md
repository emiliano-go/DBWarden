# Safe Deployment

Use a predictable release sequence for schema changes.

## Standard flow

```bash
dbwarden status --database primary
dbwarden migrate --database primary --with-backup
dbwarden history --database primary
```

For multi-database deployments:

```bash
dbwarden migrate --all --with-backup
```

## Recovery checklist

1. Check lock status
2. Inspect history and pending state
3. Decide rollback vs forward-fix
4. Execute one controlled change

## Navigation

- Previous: [CI/CD Patterns](ci-cd-patterns.md)
- Next: [CLI Reference](../cli-reference.md)
