# Operations Runbook

This runbook is for operating DBWarden safely in real environments.

## Scope

Use this guide for:

- release migrations
- rollback and recovery
- lock incidents
- checksum and drift issues

## Standard Release Procedure

1. Confirm target database and environment
2. Verify pending migrations
3. Apply migrations (with backup where needed)
4. Verify resulting state

Commands:

```bash
dbwarden status -d primary
dbwarden migrate -d primary --with-backup
dbwarden history -d primary
```

For multi-db releases:

```bash
dbwarden migrate --all --with-backup
```

## Pre-Release Checklist

- Latest code pulled
- `warden.toml` points to correct environment
- Migration files reviewed (upgrade + rollback)
- Backup strategy confirmed
- Maintenance window/rollback owner identified

## Post-Release Verification

- `dbwarden status -d <name>` shows expected applied/pending counts
- Application boot and health checks pass
- Critical queries validated
- Migration history matches deployment record

## Incident: Stuck Lock

Symptoms:

- migration command reports lock already acquired
- no active migration process is actually running

Recovery:

```bash
dbwarden lock-status -d primary
dbwarden unlock -d primary
dbwarden migrate -d primary
```

If lock keeps recurring:

- check for parallel CI/CD jobs
- enforce single migration runner per database

## Incident: Migration Failed Mid-Run

Symptoms:

- command exits with SQL or transaction error
- only part of plan applied

Recovery strategy:

1. Inspect history and current status
2. Identify exact failed migration file
3. Fix SQL or environment cause
4. Re-run `migrate` or rollback to safe point

Commands:

```bash
dbwarden history -d primary
dbwarden status -d primary
dbwarden migrate -d primary --verbose
```

## Incident: Rollback Failed

Symptoms:

- rollback section invalid for current schema state

Recovery options:

1. Create corrective manual migration using `dbwarden new`
2. Apply corrective migration forward
3. Avoid repeated failing rollback loops

Command:

```bash
dbwarden new "repair rollback state" -d primary
```

## Incident: SQL Translation Warning in Dev Mode

Symptoms:

- warnings about unsupported type/default conversion in `--dev` mode

Action:

- acceptable for local testing if fallback behavior is intentional
- use strict mode to surface failures early

Command:

```bash
dbwarden --dev --strict-translation make-migrations "validate" -d primary
```

## Incident: Duplicate URL/Target Config Error

Symptoms:

- startup/config errors for duplicate DB URL or target

Action:

- ensure each configured primary/dev URL points to a unique target
- resolve accidental overlap between `sqlalchemy_url` and `dev_database_url`

## Emergency Recovery Playbook

1. Stop deployment pipeline
2. Check lock status
3. Capture history + current status
4. Decide: rollback vs forward-fix
5. Execute one controlled change
6. Re-verify system health and migration state

Suggested command sequence:

```bash
dbwarden lock-status -d primary
dbwarden history -d primary
dbwarden status -d primary
```

## CI/CD Guardrails

- run `status` before `migrate`
- run migrations from one job only
- fail pipeline on migration non-zero exit code
- archive logs and migration files as artifacts

Example:

```yaml
- run: dbwarden status -d primary
- run: dbwarden migrate -d primary
- run: dbwarden status -d primary
```

## Operational Recommendations

- Prefer SQLite in local `--dev` loops; validate release candidate against production-like DB before shipping
- Keep migrations small and reviewable
- Always include rollback SQL
- Avoid editing old migration files after deployment
- Document every manual recovery migration in release notes
