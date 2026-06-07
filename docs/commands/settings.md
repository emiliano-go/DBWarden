# `settings`

Manage DBWarden database configuration.

## Subcommands

- `settings show` — display current configuration
- `settings default-database` — set the default database
- `settings database-add` — register a new database
- `settings database-remove` — remove a registered database
- `settings database-rename` — rename a registered database
- `settings database-set-dev` — configure dev mode for a database
- `settings database-clear-dev` — remove dev mode from a database

---

## `settings show`

Display current DBWarden configuration.

### Usage

```bash
dbwarden settings show
dbwarden settings show primary
dbwarden settings show --all
```

### Options

- `--all`, `-a` — show all configured databases

---

## `settings default-database`

Set which database is used when no `--database` flag is given.

### Usage

```bash
dbwarden settings default-database primary
```

---

## `settings database-add`

Register a new database in your DBWarden configuration.

### Usage

```bash
dbwarden settings database-add analytics \
  --type clickhouse \
  --url "http://user:pass@localhost:8123/analytics" \
  --model-path app/models/analytics
```

### Options

- `--type` — database type (`postgresql`, `sqlite`, `clickhouse`, etc.)
- `--url` — sync connection URL
- `--migrations-dir` — custom migrations directory (default: `migrations/<name>`)
- `--model-path` — model discovery path, repeatable for multiple paths
- `--dev-type` — database type for dev mode
- `--dev-url` — connection URL for dev mode
- `--overlap-models` — allow models shared with another database
- `--default` — make this the default database

---

## `settings database-remove`

Remove a database from configuration.

### Usage

```bash
dbwarden settings database-remove analytics
```

---

## `settings database-rename`

Rename a registered database handle.

### Usage

```bash
dbwarden settings database-rename primary main
```

---

## `settings database-set-dev`

Configure dev mode for an existing database.

### Usage

```bash
dbwarden settings database-set-dev primary \
  --type sqlite \
  --url "sqlite:///./development.db"
```

### Options

- `--type` — dev database type
- `--url` — dev connection URL

---

## `settings database-clear-dev`

Remove dev mode configuration from a database.

### Usage

```bash
dbwarden settings database-clear-dev primary
```

See also: [Configuration](../configuration/index.md) | [Dev Mode](../configuration/dev-mode.md)
