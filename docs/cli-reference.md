# CLI Reference

Pure command lookup for DBWarden CLI.

## Syntax

```bash
dbwarden [GLOBAL_OPTIONS] COMMAND [ARGS] [COMMAND_OPTIONS]
```

## Global options

| Option | Description |
|---|---|---|
| `--dev` | Use `dev_database_url` and `dev_database_type` for selected database |
| `--strict-translation` | Fail on unsupported/lossy dev SQLite translation |
| `--verbose` | Enable detailed logging output |
| `--help` | Show help |

## Setup and configuration

### `init`

```bash
dbwarden init
dbwarden init --database primary
```

### `settings show`

```bash
dbwarden settings show
dbwarden settings show primary
dbwarden settings show --all
```

### `settings default-database`

```bash
dbwarden settings default-database primary
```

### `settings database-add`

```bash
dbwarden settings database-add analytics \
  --type clickhouse \
  --url "http://user:pass@localhost:8123/analytics" \
  --model-path app/models/analytics
```

Options:

- `--type`
- `--url`
- `--migrations-dir`
- `--model-path` (repeatable)
- `--dev-type`
- `--dev-url`
- `--overlap-models`
- `--default`

### `settings database-remove`

```bash
dbwarden settings database-remove analytics
```

### `settings database-rename`

```bash
dbwarden settings database-rename primary main
```

### `settings database-set-dev`

```bash
dbwarden settings database-set-dev primary --type sqlite --url "sqlite:///./development.db"
```

### `settings database-clear-dev`

```bash
dbwarden settings database-clear-dev primary
```

## Migration authoring

### `make-migrations`

```bash
dbwarden make-migrations "create users table" --database primary
dbwarden make-migrations --verbose --database primary
dbwarden make-migrations --plan --database primary
dbwarden make-migrations --rename users.username:email --database primary
```

Options:

- `--database`/`-d` — Target database
- `--plan` — Print migration plan JSON without writing files
- `--verbose`/`-v` — Verbose output
- `--rename` — Repeatable. Declare a column rename in format `table.old_name:new_name`. Auto-detected renames can also be confirmed via interactive prompt (TTY) or must be declared with `--rename` in CI.

See [make-migrations](commands/make-migrations.md) for full documentation including rename detection, schema snapshots, and plan format.

### `new`

```bash
dbwarden new "manual hotfix" --database primary
dbwarden new "backfill" --database primary --version 0042
```

Options: `--database`, `--version`

### `generate-models`

```bash
dbwarden generate-models --output ./models/ --database primary
dbwarden generate-models --output ./models/ --database primary --single-file
dbwarden generate-models --database primary --tables users,posts
dbwarden generate-models --database primary --exclude-tables logs,audit
```

Options: `--output`/`-o` (default `models`), `--tables`, `--exclude-tables`, `--clickhouse-engines`, `--relationships`, `--dialect`, `--single-file`, `--database`/`-d`

### `squash`

```bash
dbwarden squash --database primary
```

Options: `--database`, `--verbose`

## Migration execution

### `migrate`

```bash
dbwarden migrate --database primary
dbwarden migrate --all
dbwarden migrate --database primary --to-version 0010
dbwarden migrate --database primary --count 2
dbwarden migrate --database primary --with-backup
dbwarden migrate --database primary --baseline --to-version 0005
```

Options:

- `--database`, `--all`
- `--to-version`, `--count`
- `--baseline`
- `--with-backup`, `--backup-dir`
- `--dry-run` (show what would be applied without executing)
- `--sandbox` (apply in a temporary sandbox database)
- `--verbose`

### `rollback`

```bash
dbwarden rollback --database primary
dbwarden rollback --database primary --count 2
dbwarden rollback --database primary --to-version 0007
```

Options: `--database`, `--count`, `--to-version`, `--verbose`

### `downgrade`

```bash
dbwarden downgrade --to 0005 --database primary
```

Options: `--to` (required), `--database`, `--verbose`

### `make-rollback`

```bash
dbwarden make-rollback migrations/primary__0005_add_table.sql
```

Generates a `.rollback.sql` file for the given migration file.

### `snapshot`

```bash
dbwarden snapshot users --database primary
```

Outputs the DDL schema of the specified table.

## Seed management

### `seed create`

```bash
dbwarden seed create "seed initial data" --database primary
dbwarden seed create "populate lookup tables" --database primary --type python
```

Options: `--database`, `--type` (`sql` or `python`, default `sql`), `--verbose`

### `seed apply`

```bash
dbwarden seed apply --database primary
dbwarden seed apply --database primary --version 0003
dbwarden seed apply --database primary --dry-run
dbwarden seed apply --all
```

Options: `--database`, `--all`, `--version`, `--dry-run`, `--verbose`

### `seed list`

```bash
dbwarden seed list --database primary
dbwarden seed list --all
```

Options: `--database`, `--all`, `--verbose`

### `seed rollback`

```bash
dbwarden seed rollback --database primary
dbwarden seed rollback --database primary --count 2
dbwarden seed rollback --database primary --to-version 0003
```

Options: `--database`, `--count`, `--to-version`, `--verbose`

## Inspection and diagnostics

### `status`

```bash
dbwarden status --database primary
dbwarden status --all
```

### `history`

```bash
dbwarden history --database primary
```

### `check-db`

```bash
dbwarden check-db --database primary
dbwarden check-db --database primary --out json
```

Output formats: `txt`, `json`, `yaml`

### `check`

```bash
dbwarden check --database primary
dbwarden check --database primary --force
dbwarden check --database primary --out json
```

Output formats: `txt`, `json`

### `diff`

```bash
dbwarden diff all --database primary
dbwarden diff models --database primary
dbwarden diff migrations --database primary
```

## Locking

### `lock-status`

```bash
dbwarden lock-status --database primary
```

### `unlock`

```bash
dbwarden unlock --database primary
```

## Utility

### `config`

```bash
dbwarden config
```

### `version`

```bash
dbwarden version
```

## Legacy compatibility commands

The `database` command group remains as a compatibility alias to `settings` flows.

Examples:

```bash
dbwarden database list
dbwarden database add analytics --type sqlite --url "sqlite:///./analytics.db"
dbwarden database remove analytics
```

Prefer `settings` commands for new workflows.


