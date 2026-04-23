# DBWarden Config Rework - Detailed Specification

## 1. Objective

Replace TOML-based configuration with a Python code-based configuration model.

This rework is a breaking change and removes `warden.toml` support immediately.

Primary outcomes:

- One runtime configuration source (`dbwarden_config()` in Python)
- Deterministic discovery and strict ambiguity errors
- First-class CLI mutators for settings management
- Full documentation migration to settings-centric UX

## 2. Scope and Breaking Changes

### In scope

- Remove all TOML read/write logic and TOML-specific command behavior.
- Add Python config discovery and loading pipeline.
- Update `dbwarden init` to scaffold or inject Python config.
- Add/replace settings mutator commands.
- Update all docs to the new model.

### Out of scope

- Runtime support for multiple config files/modules.
- Optional dual-mode (TOML + Python) compatibility period.
- Feature changes unrelated to settings resolution.

### Breaking behavior

- Any existing `warden.toml`-based project stops working until migrated.
- Any docs or scripts referencing TOML become invalid and must be updated.

## 3. Configuration Contract

### Required callable

DBWarden configuration must be exposed as a top-level function:

```python
def dbwarden_config() -> dict:
    ...
```

### Required return type

- Must return `dict`.
- Non-dict return values are hard errors.

### Canonical schema

```python
{
    "default": "primary",
    "database": {
        "primary": {
            "database_type": "postgresql",
            "sqlalchemy_url": "postgresql://user:password@localhost:5432/main",
            "migrations_dir": "migrations/primary",
            "model_paths": ["models/"],
            "postgres_schema": "public",
            "dev_database_type": "sqlite",
            "dev_database_url": "sqlite:///./development.db",
        }
    }
}
```

### Field semantics

- `default`: selected database when `-d/--database` is omitted.
- `database.<name>.sqlalchemy_url`: primary DB connection URL.
- `database.<name>.database_type`: optional explicit backend (inferred if omitted).
- `database.<name>.migrations_dir`: migration directory for that database.
- `database.<name>.model_paths`: optional list of discovery paths for model generation.
- `database.<name>.postgres_schema`: optional PostgreSQL schema override.
- `database.<name>.dev_database_url`: optional development DB URL (used with `--dev`).
- `database.<name>.dev_database_type`: optional explicit type for dev DB.

## 4. Discovery and Resolution Rules

### Rule summary

1. Search repository recursively for files named exactly `dbwarden.py`.
2. If exactly one is found, use it.
3. If more than one is found, fail (strict ambiguity rule).
4. If none are found, fallback to `DBWARDEN_CONFIG_MODULE` env var.
5. If env var is missing, fail with setup instructions.

### Performance and ignore paths

Recursive file discovery must skip:

- `.git`
- `.venv`
- `venv`
- `node_modules`
- `dist`
- `build`
- `site`
- `__pycache__`
- `.mypy_cache`
- `.pytest_cache`

### Ambiguity policy

If `>1` `dbwarden.py` files are found, DBWarden must stop and print all matched paths.

No implicit preference, no “first found” behavior.

### Environment fallback

If zero `dbwarden.py` files are found:

- Read `DBWARDEN_CONFIG_MODULE`.
- Import module by dotted path.
- Resolve and call `dbwarden_config()` from imported module.

If import fails, show import error context and expected env format.

## 5. Runtime Loading Pipeline

Conceptual algorithm:

```python
def load_runtime_config() -> dict:
    local_files = discover_dbwarden_py_files()

    if len(local_files) > 1:
        raise ConfigurationError(list_paths(local_files))

    if len(local_files) == 1:
        module = import_module_from_path(local_files[0])
    else:
        module_name = os.getenv("DBWARDEN_CONFIG_MODULE")
        if not module_name:
            raise ConfigurationError("No configuration source found")
        module = importlib.import_module(module_name)

    fn = getattr(module, "dbwarden_config", None)
    if not callable(fn):
        raise ConfigurationError("dbwarden_config() not found")

    raw = fn()
    if not isinstance(raw, dict):
        raise ConfigurationError("dbwarden_config() must return dict")

    return validate_and_normalize(raw)
```

## 6. `dbwarden init` Specification

### Command

```bash
dbwarden init [path/to/file.py]
```

### Behavior matrix

- No argument:
  - Target file is `./dbwarden.py`.
- Argument given:
  - Target file is exact user path.

For target path:

1. Create parent directories if missing.
2. If file missing, create it.
3. Inject scaffold if `dbwarden_config()` is missing.
4. Do not duplicate scaffold if already present.

### Duplicate protection

Before writing scaffold, run discovery:

- If another `dbwarden.py` already exists at a different path, fail with guidance.

### Scaffold template

Generated scaffold should include:

- imports needed for typing clarity (optional)
- `dbwarden_config()` function
- default dict with one `primary` database entry

Default example:

```python
def dbwarden_config() -> dict:
    return {
        "default": "primary",
        "database": {
            "primary": {
                "database_type": "sqlite",
                "sqlalchemy_url": "sqlite:///./app.db",
                "migrations_dir": "migrations/primary",
            }
        },
    }
```

## 7. Settings CLI (Mutators)

### Command group

```bash
dbwarden config ...
```

### Required commands

- `dbwarden config show`
- `dbwarden config default-database set <name>`
- `dbwarden config database add <name> --url ... [--type ...] [--migrations-dir ...] [--model-path ...] [--postgres-schema ...]`
- `dbwarden config database remove <name>`
- `dbwarden config database rename <old> <new>`
- `dbwarden config database set-dev <name> --url ... [--type ...]`
- `dbwarden config database clear-dev <name>`

### Mutation lifecycle (all mutators)

1. Resolve config source (discovery/env fallback).
2. Load and parse config dict.
3. Apply specific mutation.
4. Run full validation.
5. Persist updated config back to the source file.
6. Print resulting change summary.

### Mutator specifics

#### Add database

- Fails if `<name>` already exists.
- Fails on URL/target uniqueness collision.
- If `--type` missing, infer from URL.

#### Remove database

- Fails if removing current default and another default is not set in same operation.
- Optional future: `--force` behavior for default removal.

#### Rename database

- Fails if source missing.
- Fails if destination exists.
- If old name equals current default, update `default` to new name.
- Migrations directory remains unchanged unless explicitly edited.

#### Set dev database

- Sets `dev_database_url` and optional `dev_database_type`.
- If type omitted, infer from URL.
- Validates uniqueness against all primary + dev URLs/targets.

#### Clear dev database

- Removes both `dev_database_url` and `dev_database_type`.

#### Default database set

- Fails if target name does not exist.

## 8. Validation Rules

Validation remains strict and centralized:

1. `default` must exist in database map.
2. Every database entry must contain `sqlalchemy_url`.
3. `database_type` must be valid (`sqlite`, `postgresql`, `mysql`, `mariadb`, `clickhouse`) or inferable.
4. `dev_database_type` cannot exist without `dev_database_url`.
5. No duplicate normalized URLs across all primary/dev URL fields.
6. No duplicate physical database targets across all primary/dev entries.
7. In `--dev` mode, selected database must define `dev_database_url`.

## 9. Error Handling and User Messages

Mandatory explicit errors:

- Multiple config files:
  - `Multiple dbwarden.py files found. Keep exactly one.`
  - List each path on new line.
- No config source:
  - `No configuration found. Create dbwarden.py with dbwarden_config() or set DBWARDEN_CONFIG_MODULE.`
- Missing callable:
  - `dbwarden_config() not found in resolved configuration module.`
- Invalid return type:
  - `dbwarden_config() must return a dict.`
- Invalid schema:
  - Field-specific error naming offending path and key.

## 10. TOML Removal Plan

Immediate removal actions:

- Delete TOML discovery and parsing functions.
- Remove TOML file writer/update paths.
- Replace TOML-based command help text and examples.
- Ensure all command errors point to settings model.

## 11. Documentation Rework Plan

### New docs pages

1. `docs/settings.md`
   - `dbwarden_config()` contract
   - full schema reference
   - single-db and multi-db examples
   - dev SQLite recommendation
2. `docs/settings-cli.md`
   - each mutator command
   - before/after config examples
   - failure scenarios
3. `docs/migrate-from-toml.md`
   - exact mapping from TOML keys to Python dict
   - migration checklist

### Rewrite existing pages

- `docs/configuration.md`
- `docs/quickstart.md`
- `docs/cli-reference.md`
- `docs/architecture-deep-dive.md`
- `docs/operations-runbook.md`
- `README.md`

### Documentation requirements

- No remaining TOML instructions except migration guide.
- All examples use Python settings model.
- Include internal mechanics for discovery and mutator flow.

## 12. Testing Strategy

### Unit tests

- Discovery:
  - one file found
  - no file + env fallback
  - multiple files error
- Loader:
  - missing callable
  - bad return type
  - malformed schema
- Validation:
  - URL uniqueness
  - target uniqueness
  - dev invariants

### Command tests

- `init` default path creates scaffold
- `init` custom missing file creates file and directories
- `init` fails when duplicate `dbwarden.py` would exist
- Settings mutators for all required commands

### Integration tests

- Existing migration commands (`migrate`, `rollback`, `status`, `history`, `check-db`, `diff`) run against new settings loader.
- `--dev` + translation behavior remains unchanged.

## 13. Acceptance Criteria

1. DBWarden starts and operates without any TOML support.
2. Exactly-one-file discovery rule enforced (`>1` is hard fail).
3. Env module fallback works only when zero `dbwarden.py` files are found.
4. `dbwarden init` supports existing/missing custom target file paths.
5. Settings CLI supports add/remove/rename/default/set-dev/clear-dev.
6. All existing migration features remain functional with new config source.
7. Documentation is fully updated and published for the new settings model.
