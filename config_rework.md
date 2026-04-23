# DBWarden Config Rework

Status: design approved for implementation

Branch target: `config-rework`

## 1) Objective

Replace TOML configuration with a Python registration API and remove `warden.toml` support immediately.

The new model is call-based, one database per call:

```python
from dbwarden import database_config

database_config(
    database_name="primary",
    default=True,
    database_type="postgresql",
    database_url="postgresql://user:password@localhost:5432/main",
    migrations_dir="migrations/primary",
    model_paths=["models/primary"],
    dev_database_type="sqlite",
    dev_database_url="sqlite:///./development.db",
)
```

Multiple calls are allowed (one call per database configuration).

---

## 2) Locked Product Decisions

1. TOML support is removed immediately (no compatibility period).
2. Config API is predefined by DBWarden as `database_config(...)`.
3. Multiple `database_config(...)` calls are supported.
4. Exactly one `default=True` is allowed across all calls.
5. `database_name` must be a quoted string.
6. `database_url` is the canonical URL field name (not `sqlalchemy_url`).
7. `model_paths` must be present when total configured databases > 1.
8. `migrations_dir` default is `migrations/<database_name>`.
9. Model path overlap across databases is forbidden by default.
10. Model path overlap is allowed only when `overlap_models=True` is set.
11. Source resolution order:
    - discover `dbwarden.py`
    - fallback to full repo scan for `database_config(`
    - fallback to `DBWARDEN_CONFIG_MODULE`

---

## 3) Public API Contract

## 3.1 API signature

```python
database_config(
    *,
    database_name: str,
    database_type: str,
    database_url: str,
    default: bool = False,
    migrations_dir: str | None = None,
    model_paths: list[str] | None = None,
    dev_database_type: str | None = None,
    dev_database_url: str | None = None,
    overlap_models: bool = False,
) -> None
```

Behavior:

- Each call registers one database entry in an in-memory registry.
- Registry is finalized/validated after module loading.
- Missing required fields produce immediate explicit errors.

## 3.2 Required fields

- `database_name`
- `database_type`
- `database_url`

## 3.3 Optional fields and defaults

- `default=False`
- `migrations_dir=None` -> normalized to `migrations/<database_name>`
- `model_paths=None`
- `dev_database_type=None`
- `dev_database_url=None`
- `overlap_models=False`

---

## 4) Validation Rules

Validation happens after module import, against the full set of registered calls.

## 4.1 Required field validation

For each call:

- `database_name` must exist and be non-empty string
- `database_type` must exist and be valid type
- `database_url` must exist and be non-empty string

On failure: raise and name exact missing/invalid field and call location.

Examples:

- `Missing required config 'database_name' in database_config(...) call #2`
- `Missing required config 'database_type' for database 'primary'`

## 4.2 Global uniqueness constraints

Across all registered databases:

- exactly one `default=True`
- `database_name` unique
- `database_url` unique
- `migrations_dir` unique
- `dev_database_url` unique (for non-null values)

## 4.3 Physical target uniqueness

Keep existing target collision checks:

- two different URLs pointing to same effective physical DB target are invalid
- applies across primary and dev URLs

## 4.4 Dev pair constraints

- `dev_database_type` requires `dev_database_url`
- `--dev` mode requires selected DB to have `dev_database_url`

## 4.5 Model path constraints

- If total database count > 1, each database must define `model_paths`
- Overlap between model path sets is forbidden unless `overlap_models=True`

Overlap behavior:

- Default (`overlap_models=False`): no path intersection with any other DB's `model_paths`
- If `overlap_models=True` on a DB, that DB may overlap with others

Error example:

- `model_paths overlap detected between 'primary' and 'analytics'; set overlap_models=True to allow`

---

## 5) Source Discovery and Resolution

## 5.1 Resolution order

1. Recursively discover files named exactly `dbwarden.py`
2. If exactly one file found, use it
3. If more than one found, fail and print all paths
4. If none found, full scan Python files for `database_config(` occurrences
5. If exactly one candidate file found, use it
6. If multiple candidate files found, fail and print all paths
7. If no candidate found, try env var `DBWARDEN_CONFIG_MODULE`
8. If env var set, import module by dotted path
9. If env var absent, fail with setup guidance

## 5.2 Ignore directories

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

Apply ignore list to both filename and content scans.

## 5.3 Performance note

Full content scan is acceptable for small/medium repos and potentially slower in large monorepos.

Optimization path:

```bash
export DBWARDEN_CONFIG_MODULE="myapp.settings.dbwarden_settings"
```

---

## 6) Runtime Loading Pipeline

1. Resolve source via strategy in section 5.
2. Reset in-memory config registry.
3. Import resolved module (file or dotted module path).
4. During import, capture all `database_config(...)` calls.
5. Finalize and validate complete registry.
6. Build normalized runtime config structure used by existing command handlers.

Conceptual pseudocode:

```python
def load_runtime_config() -> dict:
    source = resolve_source()
    registry.reset()

    if source.kind == "file":
        import_module_from_path(source.path)
    else:
        import_module_by_name(source.module)

    entries = registry.entries()
    if not entries:
        raise ConfigurationError("No database_config(...) call found")

    cfg = finalize_entries(entries)  # uniqueness + required + defaults + normalization
    return cfg
```

---

## 7) Final Normalized Internal Shape

Although user API is call-based, normalize to this internal structure:

```python
{
    "default": "primary",
    "database": {
        "primary": {
            "database_type": "postgresql",
            "database_url": "postgresql://...",
            "migrations_dir": "migrations/primary",
            "model_paths": ["models/primary"],
            "dev_database_type": "sqlite",
            "dev_database_url": "sqlite:///./development.db",
            "overlap_models": False,
        },
        "analytics": {
            "database_type": "clickhouse",
            "database_url": "clickhouse://...",
            "migrations_dir": "migrations/analytics",
            "model_paths": ["models/analytics"],
            "dev_database_type": None,
            "dev_database_url": None,
            "overlap_models": False,
        },
    },
}
```

Note: this is internal representation only; user-facing API remains call-based.

---

## 8) `dbwarden init` Detailed Behavior

Command:

```bash
dbwarden init [path/to/file.py]
```

Behavior:

- No arg: target `./dbwarden.py`
- Arg provided: target exact path
- If parent directories missing: create them
- If file missing: create file
- Ensure import exists at top:
  - `from dbwarden import database_config`
- Ensure scaffold exists at bottom:

```python
database_config(
    database_name="primary",
    default=True,
    database_type="sqlite",
    database_url="sqlite:///./app.db",
    migrations_dir="migrations/primary",
)
```

Idempotency:

- rerunning `init` must not duplicate import or scaffold block

Safety:

- if command would create ambiguity with existing `dbwarden.py` discovery, fail with explicit guidance

---

## 9) Settings CLI (Mutators)

Command group:

```bash
dbwarden config ...
```

Required commands:

- `dbwarden config show`
- `dbwarden config default-database set <name>`
- `dbwarden config database add <name> --type <type> --url <url> [--migrations-dir ...] [--model-path ...] [--dev-type ...] [--dev-url ...] [--overlap-models] [--default]`
- `dbwarden config database remove <name>`
- `dbwarden config database rename <old> <new>`
- `dbwarden config database set-dev <name> --type <type> --url <url>`
- `dbwarden config database clear-dev <name>`

Mutator lifecycle:

1. Resolve source
2. Parse and collect existing `database_config(...)` calls
3. Apply mutation to call set
4. Re-run full validation
5. Write deterministic updated calls back to file
6. Reload and verify config resolution
7. Print concise summary

Command-specific rules:

- Add DB:
  - fail if name exists
  - fail on URL/target/migrations dir/model overlap conflicts
- Remove DB:
  - fail if not found
  - fail if removing current default and no replacement default set
- Rename DB:
  - fail if old missing or new already exists
  - transfer default flag if old was default
- Set dev:
  - set `dev_database_type`, `dev_database_url`
  - validate uniqueness/collision rules
- Clear dev:
  - clear both dev fields
- Default set:
  - enforce exactly one default

---

## 10) Error Contract

Required clear errors:

- `Multiple dbwarden.py files found. Keep exactly one.`
- `Multiple database_config(...) call sites found. Keep exactly one source or set DBWARDEN_CONFIG_MODULE.`
- `No configuration found. Add database_config(...) call(s), create dbwarden.py with dbwarden init, or set DBWARDEN_CONFIG_MODULE.`
- `Missing required config '<field>' in database_config(...)`
- `Only one database can be default=True`
- `Duplicate database_name '<name>'`
- `Duplicate database_url '<url>'`
- `Duplicate migrations_dir '<dir>'`
- `Duplicate dev_database_url '<url>'`
- `model_paths overlap detected between '<a>' and '<b>'; set overlap_models=True to allow`

All errors should include source location when available (file path and line number).

---

## 11) Immediate TOML Removal Tasks

- Remove TOML discovery/parsing functions
- Remove TOML-based config mutators
- Remove TOML references in CLI help/output
- Remove TOML examples from docs (except migration guide page)
- Replace all setup errors with new settings guidance

---

## 12) Implementation Guide (Step-by-Step)

## Phase A: Core API and registry

1. Add predefined public `database_config(...)` API
2. Add internal registry to collect call entries
3. Add registry reset/finalize utilities

## Phase B: Source resolver

1. Implement `dbwarden.py` filename discovery
2. Implement fallback content scan for `database_config(`
3. Implement env var module fallback
4. Implement ambiguity and no-source errors
5. Add per-process source cache

## Phase C: Validation and normalization

1. Implement required-field checks
2. Implement uniqueness checks
3. Implement model overlap logic with `overlap_models`
4. Implement default selection checks
5. Normalize defaults (migrations dir etc.)

## Phase D: Integrate with existing command stack

1. Swap old config loader with new runtime resolver
2. Keep existing command behavior for migrate/rollback/status/history/diff/check-db
3. Ensure `--dev` and translation features continue to work

## Phase E: Init command

1. Update init to inject import and scaffold
2. Support missing custom file creation
3. Ensure idempotency and ambiguity safety

## Phase F: Settings mutator CLI

1. Implement `config show`
2. Implement DB add/remove/rename/default-dev mutators
3. Add deterministic source rewrite
4. Add post-write reload verification

## Phase G: Tests and docs

1. Add/adjust tests per section 13
2. Rewrite docs per section 14
3. Build and publish docs

---

## 13) Test Plan

Unit tests:

- one/multiple/no `dbwarden.py` discovery
- full-scan single/multiple/no candidate behavior
- env var fallback success/failure
- missing required field errors with field name
- uniqueness rules (name/url/migrations/dev/model overlap)
- exactly-one-default rule

Command tests:

- `init` default and custom path file creation
- idempotent init behavior
- config mutators for all operations

Integration tests:

- migrate, rollback, status, history, diff, check-db under new config source
- `--dev` + translation + strict translation unchanged

---

## 14) Docs Update Layout

## 14.1 New pages

1. `docs/settings.md`
   - new API contract (`database_config(...)`)
   - required/optional fields table
   - multi-call examples
   - uniqueness and default rules
   - performance note + env optimization

2. `docs/settings-cli.md`
   - full `dbwarden config` command reference
   - before/after examples for mutators
   - common validation failures

3. `docs/migrate-from-toml.md`
   - old TOML to call-based mapping
   - migration checklist

## 14.2 Rewrite pages

- `docs/configuration.md`
- `docs/quickstart.md`
- `docs/cli-reference.md`
- `docs/architecture-deep-dive.md`
- `docs/operations-runbook.md`
- `README.md`

## 14.3 Content requirements

- remove stale TOML usage in normal docs
- include internal loader/discovery flow
- include one-default and uniqueness rules
- include large-repo performance note
- include `DBWARDEN_CONFIG_MODULE` optimization guidance

---

## 15) Acceptance Criteria

1. DBWarden runs without TOML anywhere in runtime.
2. Config resolves using: `dbwarden.py` -> full scan -> env fallback.
3. Missing required fields raise explicit errors naming the missing key.
4. Multiple calls are supported and validated.
5. Exactly one default database is enforced.
6. Name/url/migrations/dev/model uniqueness rules enforced.
7. `model_paths` required when database count > 1.
8. `dbwarden init` adds import + scaffold and creates missing target file/dirs.
9. Settings CLI mutators work and preserve valid config.
10. Documentation is fully updated and published.
