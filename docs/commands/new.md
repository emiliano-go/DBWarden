# `new`

Create a manual migration file.

## Usage

```bash
dbwarden new "manual hotfix" --database primary
dbwarden new "backfill users" --database primary --version 0042
```

## Options

- positional `description`
- `--database`, `-d`
- `--version`

## Notes

- use when change is not model-driven
- file is scaffolded with `-- upgrade` and `-- rollback` sections

See also: [Your First Migration](../tutorial/your-first-migration.md)
