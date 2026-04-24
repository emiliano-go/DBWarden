# CLI Reference

This page is a command and flag lookup.

For guided usage, start with the Tutorial pages.

## Syntax

```bash
dbwarden [GLOBAL_OPTIONS] COMMAND [ARGS] [COMMAND_OPTIONS]
```

## Global options

| Option | Description |
|--------|-------------|
| `--dev` | Use `dev_database_url`/`dev_database_type` for selected database |
| `--strict-translation` | Fail on unsupported/lossy SQL translation in dev SQLite workflows |
| `--help` | Show help |

## Configuration and setup

### `init`

Initialize DBWarden in current project.

```bash
dbwarden init
dbwarden init --database primary
```

Creates migrations directories and config scaffold if missing.

### `settings show`

Show resolved settings.

```bash
dbwarden settings show
dbwarden settings show --database primary
dbwarden settings show --all
```

### `settings default-database`

Set default database entry.

```bash
dbwarden settings default-database primary
```

### `settings database add`

Add database entry to config source.

```bash
dbwarden settings database add analytics \
  --type clickhouse \
  --url clickhouse://user:pass@localhost:8123/analytics \
  --model-path app/models/analytics
```

Common options:

- `--type`
- `--url`
- `--migrations-dir`
- `--model-path` (repeatable)
- `--dev-type`
- `--dev-url`
- `--overlap-models`
- `--default`

### `settings database remove`

```bash
dbwarden settings database remove analytics
```

### `settings database rename`

```bash
dbwarden settings database rename primary main
```

### `settings database set-dev`

```bash
dbwarden settings database set-dev primary \
  --dev-type sqlite \
  --dev-url sqlite:///./development.db
```

### `settings database clear-dev`

```bash
dbwarden settings database clear-dev primary
```

## Migration authoring

### `make-migrations`

Generate migration SQL from models.

```bash
dbwarden make-migrations -d "add billing table" --database primary
dbwarden --dev make-migrations -d "sync dev" --database primary
```

Options:

- `-d, --description` text description
- `--database` target database name
- `-v, --verbose`

### `new`

Create manual migration file.

```bash
dbwarden new -d "manual hotfix" --database primary
dbwarden new -d "backfill" --database primary --version 0042
```

Options:

- `-d, --description`
- `--version`
- `--database`

### `squash`

Combine migration files when workflow permits.

```bash
dbwarden squash --database primary
```

## Migration execution

### `migrate`

Apply pending migrations.

```bash
dbwarden migrate --database primary
dbwarden migrate --all
dbwarden migrate --database primary --to-version 0010
dbwarden migrate --database primary --count 2
dbwarden migrate --database primary --with-backup
dbwarden migrate --database primary --baseline --to-version 0005
```

Options:

- `--database`
- `--all`
- `--to-version`
- `--count`
- `--baseline`
- `--with-backup`
- `--backup-dir`
- `-v, --verbose`

### `rollback`

Rollback applied migrations.

```bash
dbwarden rollback --database primary
dbwarden rollback --database primary --count 2
dbwarden rollback --database primary --to-version 0007
```

Options:

- `--database`
- `--count`
- `--to-version`
- `-v, --verbose`

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

Inspect live schema.

```bash
dbwarden check-db --database primary
dbwarden check-db --database primary --output json
```

Options:

- `--database`
- `--output` (`txt`, `json`, `yaml`)

### `diff`

Schema comparison helper.

```bash
dbwarden diff --database primary
```

## Lock operations

### `lock-status`

```bash
dbwarden lock-status --database primary
```

### `unlock`

```bash
dbwarden unlock --database primary
```

## Utility commands

### `config`

Show active resolved configuration.

```bash
dbwarden config
```

### `version`

```bash
dbwarden version
```

## Common command patterns

### Local dev loop

```bash
dbwarden --dev make-migrations -d "sync" --database primary
dbwarden --dev migrate --database primary
dbwarden --dev status --database primary
```

### Release loop

```bash
dbwarden status --database primary
dbwarden migrate --database primary --with-backup
dbwarden history --database primary
```

### Multi-database release

```bash
dbwarden migrate --all --with-backup
dbwarden status --all
```

## Navigation

- Previous: [Safe Deployment](advanced/safe-deployment.md)
- Next: [Supported Databases](databases.md)
