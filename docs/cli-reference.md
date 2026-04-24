# CLI Reference

Pure command lookup for DBWarden CLI.

## Syntax

```bash
dbwarden [GLOBAL_OPTIONS] COMMAND [ARGS] [COMMAND_OPTIONS]
```

## Global options

| Option | Description |
|---|---|
| `--dev` | Use `dev_database_url` and `dev_database_type` for selected database |
| `--strict-translation` | Fail on unsupported/lossy dev SQLite translation |
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
```

Options: `--database`, `--verbose`

### `new`

```bash
dbwarden new "manual hotfix" --database primary
dbwarden new "backfill" --database primary --version 0042
```

Options: `--database`, `--version`

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
- `--verbose`

### `rollback`

```bash
dbwarden rollback --database primary
dbwarden rollback --database primary --count 2
dbwarden rollback --database primary --to-version 0007
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

## Navigation

- Previous: [Safe Deployment](advanced/safe-deployment.md)
- Next: [Supported Databases](databases.md)
