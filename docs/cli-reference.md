# CLI Reference

## Syntax

```bash
dbwarden [GLOBAL_OPTIONS] COMMAND [ARGS] [COMMAND_OPTIONS]
```

## Global Options

| Option | Description |
|--------|-------------|
| `--dev` | Use `dev_database_url` / `dev_database_type` for selected database |
| `--strict-translation` | Fail on lossy SQL translation in dev SQLite workflows |
| `--help`, `-h` | Show help |

## Command Index

Setup:

- `init`
- `database list`
- `database add`
- `database remove`

Migration authoring:

- `make-migrations`
- `new`
- `squash`

Migration execution:

- `migrate`
- `rollback`

Inspection:

- `status`
- `history`
- `check-db`
- `diff`

Operations:

- `lock-status`
- `unlock`
- `version`

## Common Usage Examples

```bash
# initialize
dbwarden init

# generate migration from models
dbwarden make-migrations "add billing tables" -d primary

# apply migrations
dbwarden migrate -d primary

# apply migrations in development mode
dbwarden --dev migrate -d primary

# strict translation check for dev SQLite
dbwarden --dev --strict-translation make-migrations "sync" -d primary

# inspect state
dbwarden status -d primary
dbwarden history -d primary
```

## Multi-Database Patterns

```bash
# one database
dbwarden migrate -d analytics

# all databases sequentially
dbwarden migrate --all
```

If `--all` is used, DBWarden iterates through configured database names in config order.

## Internal Behavior of Global Flags

`--dev`:

1. Enables runtime dev mode
2. Switches active config from `sqlalchemy_url` to `dev_database_url`
3. Keeps migration directory and database selection semantics unchanged

`--strict-translation`:

1. Enables strict translation mode
2. During model-to-SQL generation, unsupported SQLite conversions raise errors
3. Prevents silent fallback to `TEXT`

Conceptual callback flow:

```python
def app_callback(dev=False, strict_translation=False):
    set_dev_mode(dev)
    set_strict_translation(strict_translation)
```

## Option Cheatsheet

| Command | Main options |
|---------|--------------|
| `migrate` | `-d`, `--all`, `-c`, `-t`, `-v`, `--baseline`, `--with-backup` |
| `rollback` | `-d`, `-c`, `-t`, `-v`, `--all` |
| `make-migrations` | `-d`, `-v` |
| `check-db` | `-d`, `-o` |
| `status` | `-d`, `--all` |

## Tips

- Use `dbwarden <command> --help` for full per-command details.
- Prefer `--dev` for local iteration and `migrate -d <name>` for production-like validation.
- In CI, run `status` before and after `migrate` to make changes auditable.
