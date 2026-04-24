# CI/CD Patterns

Use a consistent migration stage in pipelines.

## Minimal pattern

```yaml
- run: dbwarden status --database primary
- run: dbwarden migrate --database primary
- run: dbwarden status --database primary
```

## Recommendations

- run migrations from one job only
- fail pipeline on non-zero migration exit
- store migration logs/artifacts for audit

## Navigation

- Previous: [Squashing Migrations](squashing-migrations.md)
- Next: [Safe Deployment](safe-deployment.md)
