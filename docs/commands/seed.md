# `seed`

Manage seed data for a database.

## Subcommands

- `seed create` — create a new seed file
- `seed apply` — apply pending seeds
- `seed list` — list seeds and their status
- `seed rollback` — roll back applied seeds

---

## `seed create`

Create a new seed file.

### Usage

```bash
dbwarden seed create "seed initial data" --database primary
dbwarden seed create "populate lookup tables" --database primary --type python
```

### Options

- `--database`, `-d` — target database handle
- `--type` — `sql` (default) or `python`
- `--verbose`, `-v`

---

## `seed apply`

Apply pending seeds.

### Usage

```bash
dbwarden seed apply --database primary
dbwarden seed apply --database primary --version 0003
dbwarden seed apply --database primary --dry-run
dbwarden seed apply --all
```

### Options

- `--database`, `-d`
- `--all`, `-a` — apply across all configured databases
- `--version` — apply up to this seed version
- `--dry-run` — preview without executing
- `--verbose`, `-v`

---

## `seed list`

List seeds and their applied status.

### Usage

```bash
dbwarden seed list --database primary
dbwarden seed list --all
```

### Options

- `--database`, `-d`
- `--all`, `-a`
- `--verbose`, `-v`

---

## `seed rollback`

Roll back applied seeds.

### Usage

```bash
dbwarden seed rollback --database primary
dbwarden seed rollback --database primary --count 2
dbwarden seed rollback --database primary --to-version 0003
```

### Options

- `--database`, `-d`
- `--count` — number of seeds to roll back (default: 1)
- `--to-version` — roll back to this seed version
- `--verbose`, `-v`

See also: [Seed Management](../seeds.md)
