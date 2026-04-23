# DBWarden Config Rework - Final Detailed Spec (Predefined `dbwarden_config(...)` API)

## 1) Summary

DBWarden will move from TOML configuration to a Python registration API.

Instead of reading `warden.toml`, users will register configuration by calling a predefined DBWarden function inside a Python module:

```python
from dbwarden import dbwarden_config

dbwarden_config({
    "default": "primary",
    "database": {
        "primary": {
            "database_type": "sqlite",
            "sqlalchemy_url": "sqlite:///./app.db",
            "migrations_dir": "migrations/primary",
        }
    },
})
```

This is a breaking change. `warden.toml` support is removed immediately.

---

## 2) Locked Product Decisions

1. **No TOML compatibility phase**. Remove TOML support now.
2. **Config is registered by calling DBWarden’s predefined function**:
   - `dbwarden_config(<dict>)`
3. **Exactly one registration call is allowed** in the resolved settings module.
4. DBWarden discovers `dbwarden.py` recursively in the repo.
5. If more than one `dbwarden.py` is found, DBWarden fails.
6. If no `dbwarden.py` is found, DBWarden falls back to `DBWARDEN_CONFIG_MODULE`.
7. `dbwarden init [path/to/file.py]` must:
   - add import at top: `from dbwarden import dbwarden_config`
   - add registration scaffold at bottom
   - create file if it does not exist
8. Settings mutator CLI must support add/remove/rename/default/set-dev/clear-dev.

---

## 3) API Contract

### 3.1 Public registration API

DBWarden exports:

```python
dbwarden_config(config: dict) -> None
```

Behavior:

- Accepts one argument: `config` (dict)
- Stores config in internal runtime registry for later resolution
- If called more than once during one module load cycle, raises a duplicate registration error

### 3.2 Required usage style in user settings file

```python
from dbwarden import dbwarden_config

dbwarden_config({...})
```

No user-defined callback/function contract is required.

### 3.3 Exactly-one-call rule

For the resolved settings module/file:

- 0 `dbwarden_config(...)` calls -> error
- 1 call -> valid
- >1 calls -> error

---

## 4) Config Schema Contract

### 4.1 Top-level shape

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
    },
}
```

### 4.2 Semantics

- `default` (required): default database key used when `-d` is omitted
- `database` (required): mapping of db name -> db config
- `sqlalchemy_url` (required per db)
- `database_type` (optional; inferred from URL)
- `migrations_dir` (optional; default `migrations/<name>`)
- `model_paths` (optional list[str])
- `postgres_schema` (optional)
- `dev_database_url` (optional)
- `dev_database_type` (optional, requires `dev_database_url`)

### 4.3 Type/value constraints

- database type must be one of: `sqlite`, `postgresql`, `mysql`, `mariadb`, `clickhouse`
- URLs must be valid SQLAlchemy URLs or produce clear validation errors

---

## 5) Discovery and Resolution

### 5.1 Resolution order

1. Find all files named `dbwarden.py` recursively from workspace root.
2. If exactly 1 found: use it.
3. If >1 found: fail and print all matching paths.
4. If 0 found: read env var `DBWARDEN_CONFIG_MODULE`.
5. If env var exists: import that module and resolve registration.
6. If env var missing: fail with setup instructions.

### 5.2 Directory ignore list

The recursive scan must skip:

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

### 5.3 Ambiguity handling

If multiple `dbwarden.py` are found, DBWarden **must not guess**.

Error should include:

- one-line reason
- exact list of matching paths
- guidance to keep only one file or use env module fallback path strategy

---

## 6) Runtime Loading Pipeline

### 6.1 Internal flow

1. Resolve source (file or env module).
2. Reset transient config registry for clean load.
3. (Recommended) AST parse resolved source to count `dbwarden_config(...)` calls.
4. Enforce exactly-one-call rule before import when source file is available.
5. Import/execute module.
6. Read registered config from runtime registry.
7. Validate and normalize config dict.
8. Return normalized config object used by command handlers.

### 6.2 Conceptual pseudocode

```python
def load_runtime_config() -> dict:
    source = resolve_settings_source()  # file path or module name

    reset_config_registry()

    if source.is_file:
        call_count = count_dbwarden_config_calls_ast(source.path)
        if call_count == 0:
            raise ConfigurationError("No dbwarden_config(...) call found")
        if call_count > 1:
            raise ConfigurationError("Multiple dbwarden_config(...) calls found")

        import_module_from_file(source.path)
    else:
        import_module_by_name(source.module)

    raw = get_registered_config_from_registry()
    if raw is None:
        raise ConfigurationError("dbwarden_config(...) did not register config")
    if not isinstance(raw, dict):
        raise ConfigurationError("dbwarden_config(...) must receive a dict")

    return validate_and_normalize(raw)
```

### 6.3 Registry safety behavior

- Registry should allow one successful set per load cycle.
- If second call occurs, raise deterministic duplicate-registration error.
- Clear registry between command executions/tests to avoid cross-test contamination.

---

## 7) `dbwarden init` Detailed Spec

### 7.1 Command

```bash
dbwarden init [path/to/file.py]
```

### 7.2 Path resolution

- No arg -> `./dbwarden.py`
- With arg -> exact provided path

### 7.3 File behavior

- If parent dirs missing: create them
- If file missing: create file
- If file exists: preserve existing content and inject missing pieces only

### 7.4 Injection requirements

Must ensure both exist exactly once:

1. Import line near top:

```python
from dbwarden import dbwarden_config
```

2. Scaffold registration at bottom:

```python
dbwarden_config({
    "default": "primary",
    "database": {
        "primary": {
            "database_type": "sqlite",
            "sqlalchemy_url": "sqlite:///./app.db",
            "migrations_dir": "migrations/primary",
        }
    },
})
```

### 7.5 Idempotency

- Running `dbwarden init` repeatedly must not duplicate import or scaffold.
- If both already present, print informational success and no changes.

### 7.6 Duplicate-file guard

Before writing default/no-arg scaffold, run discovery:

- if another `dbwarden.py` exists elsewhere, fail with explicit ambiguity guidance.

---

## 8) Settings CLI Spec

### 8.1 Command group

```bash
dbwarden config ...
```

### 8.2 Commands

- `dbwarden config show`
- `dbwarden config default-database set <name>`
- `dbwarden config database add <name> --url ... [--type ...] [--migrations-dir ...] [--model-path ...] [--postgres-schema ...]`
- `dbwarden config database remove <name>`
- `dbwarden config database rename <old> <new>`
- `dbwarden config database set-dev <name> --url ... [--type ...]`
- `dbwarden config database clear-dev <name>`

### 8.3 Mutator lifecycle (all mutator commands)

1. Resolve source.
2. Parse source and extract dict argument from single `dbwarden_config(...)` call.
3. Apply mutation.
4. Run full config validation.
5. Write updated dict back in deterministic format.
6. Re-load to verify parse/registration still succeeds.
7. Print before/after summary.

### 8.4 Command-specific rules

#### Add database

- fail if name already exists
- infer type from URL if `--type` omitted
- fail on URL or target collisions

#### Remove database

- fail if database does not exist
- fail if removing default without setting a new default first/within command

#### Rename database

- fail if old does not exist
- fail if new already exists
- if old is default, update default to new
- preserve existing field values unless explicitly changed

#### Set dev database

- set `dev_database_url`
- set/infer `dev_database_type`
- validate uniqueness against all primary + dev entries

#### Clear dev database

- remove both `dev_database_url` and `dev_database_type`

#### Set default database

- fail if target key does not exist

---

## 9) Validation Rules

Validation is centralized and applied after load and after each mutator write.

Rules:

1. `default` exists and references a configured database
2. each database has `sqlalchemy_url`
3. database type is valid or inferable
4. `dev_database_type` cannot exist without `dev_database_url`
5. no duplicate normalized URLs across all primary/dev URLs
6. no duplicate physical DB targets across all primary/dev targets
7. in `--dev`, selected DB must have `dev_database_url`

---

## 10) Error Messages and Diagnostics

Required failures:

- Multiple config files:
  - `Multiple dbwarden.py files found. Keep exactly one.`
- No source:
  - `No configuration found. Create dbwarden.py with 'dbwarden init' or set DBWARDEN_CONFIG_MODULE.`
- No registration call:
  - `No dbwarden_config(...) call found in resolved config module.`
- Multiple registration calls:
  - `Multiple dbwarden_config(...) calls found. Keep exactly one.`
- Invalid payload type:
  - `dbwarden_config(...) requires a dict payload.`
- Validation errors:
  - precise field path and database name where relevant

Diagnostics should include resolved source location for easier debugging.

---

## 11) TOML Removal Tasks

Immediate codebase cleanup tasks:

- remove TOML discovery/parsing helpers
- remove TOML write/update code paths
- remove TOML references from command help/output
- remove TOML docs (except migration guide section)
- replace error messages with settings-centric guidance

---

## 12) Implementation Precision Notes

### 12.1 Parsing strategy for mutators

Use AST-based extraction for `dbwarden_config({...})` payload in source file when possible.

- Safer than regex string slicing
- resilient to whitespace/comments
- enables exact-one-call enforcement

### 12.2 Write-back formatting strategy

- Use deterministic pretty formatting for dict literal output
- preserve file content outside managed registration block when possible
- avoid non-ASCII unless already present

### 12.3 Managed-block recommendation

For future stability, include optional markers around generated scaffold:

```python
# DBWARDEN_CONFIG_START
dbwarden_config({...})
# DBWARDEN_CONFIG_END
```

Mutators can then safely target this region.

### 12.4 Import side effects

Since module import executes Python code:

- documentation must recommend keeping settings module side-effect free
- loader should surface exceptions with module path context

---

## 13) Test Plan

### 13.1 Unit tests

- discovery:
  - one file found
  - zero files + env fallback
  - multiple files fail
- registration:
  - zero calls fail
  - one call works
  - multiple calls fail
  - non-dict payload fails
- validation:
  - default missing
  - URL missing
  - dev invariants
  - URL/target uniqueness

### 13.2 Command tests

- `init` no arg creates `dbwarden.py`
- `init path/to/file.py` creates missing dirs/file
- `init` idempotency
- config mutators for all required operations

### 13.3 Integration tests

- migrate/rollback/status/history/check-db/diff under new config model
- `--dev` behavior unchanged
- strict translation behavior unchanged

---

## 14) Docs Rework Plan

### 14.1 New docs pages

1. `docs/settings.md`
   - predefined API usage (`dbwarden_config({...})`)
   - schema reference
   - single/multi-db examples
2. `docs/settings-cli.md`
   - all mutators with before/after examples
3. `docs/migrate-from-toml.md`
   - old TOML -> new registration payload mapping

### 14.2 Rewrite existing pages

- `docs/configuration.md`
- `docs/quickstart.md`
- `docs/cli-reference.md`
- `docs/architecture-deep-dive.md`
- `docs/operations-runbook.md`
- `README.md`

### 14.3 Documentation quality requirements

- no stale TOML usage in normal setup docs
- include internals for discovery and loading
- include mutation safety and failure handling

---

## 15) Rollout and Acceptance Criteria

Accepted when all are true:

1. DBWarden runs without TOML support anywhere in runtime.
2. Config resolves from exactly one `dbwarden.py` or env module fallback.
3. Exactly-one `dbwarden_config(...)` call is enforced.
4. `dbwarden init` injects import top + scaffold bottom and creates missing files.
5. Settings CLI supports add/remove/rename/default/set-dev/clear-dev.
6. Existing migration features remain stable.
7. Docs are fully updated and published with new settings model.
