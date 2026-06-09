---
seo:
  title: '`seed` - DBWarden Documentation'
  description: 'seed Manage seed data for a database. Subcommands seed create: create
    a new seed file seed apply: apply pending seeds seed list: list seeds and their
    status seed rollback: roll back applied seeds...'
  canonical: https://emiliano-gandini-outeda.github.io/DBWarden/commands/seed/
  robots: index,follow
  og:
    type: website
    title: '`seed` - DBWarden Documentation'
    description: 'seed Manage seed data for a database. Subcommands seed create: create
      a new seed file seed apply: apply pending seeds seed list: list seeds and their
      status seed rollback: roll back applied seeds...'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/seed/
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    site_name: DBWarden Documentation
  twitter:
    card: summary_large_image
    title: '`seed` - DBWarden Documentation'
    description: 'seed Manage seed data for a database. Subcommands seed create: create
      a new seed file seed apply: apply pending seeds seed list: list seeds and their
      status seed rollback: roll back applied seeds...'
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
  schema_jsonld:
    '@context': https://schema.org
    '@type': WebPage
    name: '`seed` - DBWarden Documentation'
    url: https://emiliano-gandini-outeda.github.io/DBWarden/commands/seed/
    description: 'seed Manage seed data for a database. Subcommands seed create: create
      a new seed file seed apply: apply pending seeds seed list: list seeds and their
      status seed rollback: roll back applied seeds...'
    image: https://emiliano-gandini-outeda.github.io/DBWarden/assets/icon.png
    publisher:
      '@type': Organization
      name: Emiliano Gandini Outeda
---

# `seed`

Manage seed data for a database.

## Subcommands

- `seed create`: create a new seed file
- `seed apply`: apply pending seeds
- `seed list`: list seeds and their status
- `seed rollback`: roll back applied seeds

---

## `seed create`

Create a new seed file.

### Usage

```bash
dbwarden seed create "seed initial data" --database primary
dbwarden seed create "populate lookup tables" --database primary --type python
```

### Options

- `--database`, `-d`: target database handle
- `--type`: `sql` (default) or `python`
- `--seed-table`: custom seed tracking table name (default: `_dbwarden_seeds`)
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
- `--all`, `-a`: apply across all configured databases
- `--version`: apply up to this seed version
- `--seed-table`: custom seed tracking table name
- `--dry-run`: preview without executing
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
- `--count`: number of seeds to roll back (default: 1)
- `--to-version`: roll back to this seed version
- `--verbose`, `-v`

See also: [Seed Management](../seeds.md)
