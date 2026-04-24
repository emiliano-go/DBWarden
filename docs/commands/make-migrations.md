# `make-migrations`

Generate SQL migration file(s) from SQLAlchemy models.

## Usage

```bash
dbwarden make-migrations "create users table" --database primary
dbwarden make-migrations "sync models" --database primary --verbose
```

## Options

- positional `description`
- `--database`, `-d`
- `--verbose`, `-v`

## Notes

- generated file includes both `-- upgrade` and `-- rollback`
- if no models are discovered, configure `model_paths` explicitly
- with `--dev`, translation can target dev SQLite behavior

See also: [Migration File Format](../migration-files.md)
