# `database` (legacy compatibility)

Legacy compatibility command group for database management.

Prefer `settings` commands for new workflows.

## Usage

```bash
dbwarden database list
dbwarden database add <name> --url <url> --type <type>
dbwarden database remove <name>
```

## Compatibility mapping

- `database list` -> `settings show --all`
- `database add` -> `settings database-add`
- `database remove` -> `settings database-remove`

## Notes

- `database` remains available to ease migration from older workflows
- configuration source is Python (`database_config(...)`), not TOML

See also: [CLI Reference](../cli-reference.md)
