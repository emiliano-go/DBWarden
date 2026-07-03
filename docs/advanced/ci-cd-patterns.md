---
seo:
  title: CI/CD Patterns - DBWarden Documentation
  canonical: https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns
  robots: index,follow
  og:
    type: website
    title: CI/CD Patterns - DBWarden Documentation
    description: Patterns for running DBWarden migrations in automated pipelines.
    url: https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    image:width: 128
    image:height: 128
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: CI/CD Patterns - DBWarden Documentation
    description: Patterns for running DBWarden migrations in automated pipelines.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
  description: Patterns for running DBWarden migrations in automated pipelines.
  schema_jsonld:
  - '@context': https://schema.org
    '@type': WebPage
    name: CI/CD Patterns - DBWarden Documentation
    url: https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns
    description: Patterns for running DBWarden migrations in automated pipelines.
    image: https://dbwarden.emiliano-go.com/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
  - '@context': https://schema.org
    '@type': BreadcrumbList
    itemListElement:
    - '@type': ListItem
      position: 1
      name: Advanced
      item: https://dbwarden.emiliano-go.com/advanced
    - '@type': ListItem
      position: 2
      name: CI/CD Patterns
      item: https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns
seo_html: "<title>CI/CD Patterns - DBWarden Documentation</title>\n<meta name=\"description\"\
  \ content=\"Patterns for running DBWarden migrations in automated pipelines.\">\n\
  <link rel=\"canonical\" href=\"https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns\"\
  >\n<meta name=\"robots\" content=\"index,follow\">\n<meta property=\"og:type\" content=\"\
  website\">\n<meta property=\"og:title\" content=\"CI/CD Patterns - DBWarden Documentation\"\
  >\n<meta property=\"og:description\" content=\"Patterns for running DBWarden migrations\
  \ in automated pipelines.\">\n<meta property=\"og:url\" content=\"https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns\"\
  >\n<meta property=\"og:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<meta property=\"og:image:width\" content=\"128\">\n<meta property=\"og:image:height\"\
  \ content=\"128\">\n<meta property=\"og:site_name\" content=\"DBWarden Documentation\"\
  >\n<meta name=\"twitter:card\" content=\"summary_large_image\">\n<meta name=\"twitter:title\"\
  \ content=\"CI/CD Patterns - DBWarden Documentation\">\n<meta name=\"twitter:description\"\
  \ content=\"Patterns for running DBWarden migrations in automated pipelines.\">\n\
  <meta name=\"twitter:image\" content=\"https://dbwarden.emiliano-go.com/assets/icon.png\"\
  >\n<script type=\"application/ld+json\">\n[\n  {\n    \"@context\": \"https://schema.org\"\
  ,\n    \"@type\": \"WebPage\",\n    \"name\": \"CI/CD Patterns - DBWarden Documentation\"\
  ,\n    \"url\": \"https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns\",\n\
  \    \"description\": \"Patterns for running DBWarden migrations in automated pipelines.\"\
  ,\n    \"image\": \"https://dbwarden.emiliano-go.com/assets/icon.png\",\n    \"\
  publisher\": {\n      \"@type\": \"Organization\",\n      \"name\": \"Emiliano Gandini\
  \ Outeda\"\n    }\n  },\n  {\n    \"@context\": \"https://schema.org\",\n    \"\
  @type\": \"BreadcrumbList\",\n    \"itemListElement\": [\n      {\n        \"@type\"\
  : \"ListItem\",\n        \"position\": 1,\n        \"name\": \"Advanced\",\n   \
  \     \"item\": \"https://dbwarden.emiliano-go.com/advanced\"\n      },\n      {\n\
  \        \"@type\": \"ListItem\",\n        \"position\": 2,\n        \"name\": \"\
  CI/CD Patterns\",\n        \"item\": \"https://dbwarden.emiliano-go.com/advanced/ci-cd-patterns\"\
  \n      }\n    ]\n  }\n]\n</script>\n"
---

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

      - run: uv add -e ".[migrations]"

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
    - uv add -e ".[migrations]"
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

## Sandbox testing in PR pipelines

Instead of running against a shared staging database, use `--sandbox`
to apply migrations to a temporary in-memory SQLite database or a
Docker-backed instance. This isolates PR checks from each other:

```yaml
sandbox-check:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - run: uv add -e ".[migrations,testcontainers]"
    - name: Apply migrations to sandbox
      run: dbwarden migrate --sandbox --database primary
```

The sandbox starts a fresh database, applies all pending migrations,
reports results, and tears down. It never touches the real database.

## Dry-run check in PR pipelines

Use `--dry-run` to preview SQL without any database access:

```yaml
migration-check:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - run: uv add -e ".[migrations]"
    - name: Check for pending migrations
      run: dbwarden status --database primary
      env:
        DATABASE_URL: ${{ secrets.STAGING_DATABASE_URL }}
```

This surfaces "pending migrations exist" warnings in PR checks without
modifying the database.

For a deeper check that validates the SQL actually runs, chain
`--dry-run` before `--sandbox`:

```yaml
- name: Preview SQL
  run: dbwarden migrate --dry-run --database primary

- name: Validate in sandbox
  run: dbwarden migrate --sandbox --database primary
```

## Plan output in deploy pipelines

The `make-migrations --plan` flag prints the generated migration plan
as JSON without writing files. Use it in deploy pipelines to capture
what would be generated as a deploy artifact:

```yaml
- name: Generate migration plan
  run: dbwarden make-migrations --database primary --plan > plan.json

- name: Upload plan artifact
  uses: actions/upload-artifact@v4
  with:
    name: migration-plan-${{ github.sha }}
    path: plan.json
```

The plan JSON includes detected changes, operation counts, and
auto-generated migration names.

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
- Run `dbwarden status` before and after `migrate`; before confirms what will run, after confirms nothing is pending

See also: [Safe Deployment](safe-deployment.md) | [Credentials and Secrets](../configuration/credentials.md) | [Migration Locking](migration-locking.md) | [Cookbook: Offline & CI](../cookbook/04-offline-ci.md)
