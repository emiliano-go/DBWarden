# CI/CD Patterns

Patterns for running DBWarden migrations in automated pipelines.

## Core principle

Run migrations from exactly one job. Serialize migration and deploy. Never run `migrate` in parallel across multiple agents or containers targeting the same database.

## GitHub Actions

### Minimal migration job

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -e ".[migrations]"

      - name: Check migration status
        run: dbwarden status --database primary
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Apply migrations
        run: dbwarden migrate --database primary
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - name: Verify post-migration status
        run: dbwarden status --database primary
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: ...
```

The `needs: migrate` dependency ensures migrations are fully applied before the application starts.

### Preventing concurrent migration runs

```yaml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false
```

`cancel-in-progress: false` queues duplicate runs instead of cancelling mid-flight, which avoids leaving a stale lock on the database.

### Multi-database migration

```yaml
- name: Apply all migrations
  run: dbwarden migrate --all
  env:
    PRIMARY_DATABASE_URL: ${{ secrets.PRIMARY_DATABASE_URL }}
    ANALYTICS_DATABASE_URL: ${{ secrets.ANALYTICS_DATABASE_URL }}
```

Or migrate databases sequentially to control order:

```yaml
- name: Migrate primary
  run: dbwarden migrate --database primary
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

- name: Migrate analytics
  run: dbwarden migrate --database analytics
  env:
    ANALYTICS_DATABASE_URL: ${{ secrets.ANALYTICS_DATABASE_URL }}
```

### With backup before migration

```yaml
- name: Apply migrations with backup
  run: |
    dbwarden migrate --database primary \
      --with-backup \
      --backup-dir ./migration-backups
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

- name: Upload backup artifact
  uses: actions/upload-artifact@v4
  with:
    name: migration-backup-${{ github.sha }}
    path: ./migration-backups/
    retention-days: 30
```

## GitLab CI

```yaml
stages:
  - migrate
  - deploy

migrate:
  stage: migrate
  image: python:3.12
  script:
    - pip install -e ".[migrations]"
    - dbwarden status --database primary
    - dbwarden migrate --database primary
    - dbwarden status --database primary
  variables:
    DATABASE_URL: $DATABASE_URL  # set in GitLab CI/CD settings as masked variable
  resource_group: production-database  # prevents concurrent runs

deploy:
  stage: deploy
  needs: [migrate]
  script:
    - ...
```

`resource_group` serializes the migrate job across concurrent pipelines.

## Dry-run check in PR pipelines

Run a non-destructive check on pull requests without applying migrations:

```yaml
migration-check:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - run: pip install -e ".[migrations]"
    - name: Check for pending migrations
      run: dbwarden status --database primary
      env:
        DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}
```

This surfaces "pending migrations exist" warnings in PR checks without modifying the database.

## Exit codes

DBWarden exits non-zero on:

- Migration failure
- Checksum mismatch
- Lock acquisition failure
- Configuration error

CI pipelines treat non-zero as job failure by default. No extra configuration needed.

## Recommendations

- Store `DATABASE_URL` as an encrypted secret, not a plain environment variable
- Archive migration output logs as artifacts for audit trails
- Use `dbwarden history` output as a post-migration artifact
- Run `dbwarden status` before and after `migrate` — before confirms what will run, after confirms nothing is pending

See also: [Safe Deployment](safe-deployment.md) | [Credentials and Secrets](../configuration/credentials.md) | [Migration Locking](migration-locking.md)
