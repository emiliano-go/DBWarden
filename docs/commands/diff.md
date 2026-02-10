# diff Command

Show structural differences between models and database.

## Description

The `diff` command compares your SQLAlchemy model definitions against the actual database schema to identify discrepancies.

## Usage

```bash
dbwarden diff [type]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `type` | Type of diff: `models`, `migrations`, `all` (default: `all`) |

## Options

| Option | Description |
|--------|-------------|
| `--verbose`, `-v` | Enable verbose logging |

## Examples

### Compare Models vs Database

```bash
dbwarden diff
```

### Verbose Output

```bash
dbwarden diff --verbose
```

## What It Shows

### New Tables (in models, not in DB)

Tables defined in your models but not yet created in the database.

### Missing Columns (in DB, not in models)

Columns in the database that don't have corresponding model definitions.

### Type Mismatches

Columns where the data type differs between model and database.

### Missing Indexes

Indexes that exist in models (via SQLAlchemy) but not in database.

## Use Cases

### Before Migration

Check what will be created:

```bash
dbwarden diff
# Shows tables/columns that need to be added
```

### After Migration Issues

Debug schema inconsistencies:

```bash
dbwarden diff
# Shows discrepancies
```

### Schema Drift Detection

Identify when database schema doesn't match code:

```bash
dbwarden diff
# Compare current state
```

## Requirements

For `diff` to work effectively:

1. **Models must be defined**: SQLAlchemy models in `models/` directory
2. **model_paths**: Must be set in warden.toml or auto-discovery must find models
3. **Migrations table exists**: At least one migration applied

## Troubleshooting

### No Models Found

```
No SQLAlchemy models found. Please:
  1. Create models/ directory with your SQLAlchemy models
  2. Or set model_paths in warden.toml
```

Set model paths in `warden.toml`:
```toml
model_paths = ["models/", "app/models/"]
```

### No Migrations Table

```
No migrations table found. Run 'dbwarden migrate' first.
```

Apply at least one migration before using `diff`.

## Best Practices

1. **Run before migrations**: See what changes are pending
2. **Run after issues**: Debug schema problems
3. **Use with check-db**: Combine for comprehensive view

## See Also

- [check-db](check-db.md): Inspect current database schema
- [make-migrations](make-migrations.md): Generate migrations from differences
- [models](../models.md): SQLAlchemy model integration
