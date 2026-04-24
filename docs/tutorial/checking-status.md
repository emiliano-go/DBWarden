# Checking Status

Use status and history commands to understand migration state.

These commands should be part of your normal development and deployment flow.

## Status

```bash
dbwarden status --database primary
dbwarden history --database primary
```

Reference: [CLI Reference](../cli-reference.md)

## Navigation

- Previous: [Rolling Back](rolling-back.md)
- Next: [Dev Mode](dev-mode.md)

Shows applied and pending versions.

Use this before migrate (to understand plan) and after migrate (to confirm result).

## History

```bash
dbwarden history --database primary
```

Shows execution records with order and timestamps.

Use history for audit and incident analysis.

## Multi-database status checks

```bash
dbwarden status --all
```

This is useful in systems where one release touches several stores.

## Inspect schema

```bash
dbwarden check-db --database primary
```

Use this to compare expected schema and live database state.

## Recommended operational loop

```bash
dbwarden status --database primary
dbwarden migrate --database primary
dbwarden status --database primary
dbwarden history --database primary
```
