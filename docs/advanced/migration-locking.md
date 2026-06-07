# Migration Locking

DBWarden uses a database-level lock to prevent concurrent schema mutation. This page explains how it works, what happens when it fails, and how to recover from a stuck lock.

## How locking works

When `dbwarden migrate` runs, it:

1. Acquires a lock row in the `dbwarden_lock` table (created on first use)
2. Executes all pending migrations within that lock
3. Releases the lock on success or failure

The lock is stored in the target database itself — no external service (Redis, filesystem) is required.

If a second `migrate` invocation starts while the first holds the lock, it fails immediately with:

```
MigrationLockError: Database 'primary' is locked by another migration process.
Use 'dbwarden lock-status --database primary' to inspect the lock.
```

DBWarden does not retry on lock failure. The calling process (CI job, deploy script) must decide whether to retry or abort.

## Inspecting lock state

```bash
dbwarden lock-status --database primary
```

Output when unlocked:

```
primary: unlocked
```

Output when locked:

```
primary: LOCKED
  locked_at: 2026-06-06 14:32:11 UTC
  locked_by: migrate
  pid: 84921
```

The `locked_at` timestamp and `pid` are recorded at acquisition time. Use these to determine whether the lock is held by a live process or is stale.

## When a migration fails mid-run

If a migration raises an error after partial execution:

1. DBWarden rolls back the in-flight transaction (if the database supports transactional DDL — PostgreSQL does, MySQL does not)
2. The lock is released
3. The CLI exits non-zero

For PostgreSQL, partial application within a migration file is rolled back atomically. The migration remains in "pending" state.

For MySQL and databases without transactional DDL, partial application is possible. Inspect the database state manually before retrying.

## Stuck lock recovery

A lock becomes stale when:

- The migration process was killed (SIGKILL, OOM, machine restart)
- A CI job was cancelled mid-run
- A deploy container was stopped before migrate completed

**Before unlocking, confirm no migration is running:**

```bash
# Check if the PID from lock-status is still alive
ps aux | grep <pid>

# Or check your deployment logs / CI job status
```

If the process is genuinely dead:

```bash
# 1. Confirm lock state
dbwarden lock-status --database primary

# 2. Inspect migration history to see what ran last
dbwarden history --database primary

# 3. Check pending migrations
dbwarden status --database primary

# 4. Release the stale lock
dbwarden unlock --database primary

# 5. Retry migration
dbwarden migrate --database primary
```

## When NOT to use `unlock`

Do not run `unlock` if:

- You are unsure whether a migration process is still running
- The `locked_at` timestamp is recent (within seconds or minutes) — the process may still be alive
- Multiple processes share a database and you cannot confirm all are idle

Releasing a lock held by a live migration process will allow a second migration to start concurrently, which can corrupt schema state.

## Preventing concurrent migration in CI

In CI/CD, run migrations from a single job with no parallelism:

```yaml
# GitHub Actions — serialize via job dependency
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - run: dbwarden migrate --database primary
  deploy:
    needs: migrate
    ...
```

If your pipeline can trigger multiple concurrent deploys, add a concurrency group:

```yaml
concurrency:
  group: migrate-${{ github.ref }}
  cancel-in-progress: false
```

`cancel-in-progress: false` queues the second run instead of cancelling it, which avoids orphaned locks from killed jobs.

See also: [Safe Deployment](safe-deployment.md) | [CI/CD Patterns](ci-cd-patterns.md) | [`lock` commands](../commands/lock.md)
