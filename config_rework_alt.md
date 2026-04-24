# DBWarden Config Rework (Alternative)

Using cattrs for validation and type coercion.

Status: pending implementation

Branch target: `config-rework-alt`

## 1) Objective

Replace TOML configuration with a Python registration API using `attrs` + `cattrs` for validation and type coercion.

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
10. `overlap_models=True` allows a DB to accept paths from other databases.
11. Source resolution order:
    - discover `dbwarden.py`
    - fallback to full repo scan for `database_config(`
    - fallback to `DBWARDEN_CONFIG_MODULE`

---

## 3) cattrs Integration

DBWarden uses `cattrs` + `attrs` for:

- Structured validation with field-level error messages
- Type coercion (e.g., string URLs, int ports)
- Rich error reporting via `cattrs.transform_error()`
- Extensible validators

### Dependencies

```toml
[project.optional-dependencies]
config = [
    "cattrs>=22.1",
    "attrs>=22.1",
]
```

Core CLI-only installs stay lean:

```toml
[project.dependencies]
# No cattrs required for base CLI
```

### Why cattrs?

| Benefit | Description |
|---------|-------------|
| Rich validation errors | Field paths like `$.databases.primary.database_type` |
| Type coercion | Automatic conversion (e.g., `"5432"` → `5432`) |
| Organized validators | attrs validators compose cleanly |
| Battle-tested | Used in many production projects |
| Extensible | Register custom structuring hooks |

---

## 4) Public API Contract

## 4.1 API signature

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

- Each call validates and registers one database entry in an in-memory registry.
- Registry is finalized/validated after module loading.
- cattrs handles type coercion and field-level validation.
- Global uniqueness checks happen at finalize time.

## 4.2 Required fields

- `database_name`
- `database_type`
- `database_url`

## 4.3 Optional fields and defaults

- `default=False`
- `migrations_dir=None` -> normalized to `migrations/<database_name>`
- `model_paths=None`
- `dev_database_type=None`
- `dev_database_url=None`
- `overlap_models=False`

---

## 5) attrs + cattrs Schema

```python
# dbwarden/config/schema.py

from __future__ import annotations
import cattrs
from attrs import define, field, validators
from typing import Literal

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]

VALID_DATABASE_TYPES = frozenset({"sqlite", "postgresql", "mysql", "mariadb", "clickhouse"})

# Custom validator for database_type
def _validate_database_type(self, attribute, value):
    if value not in VALID_DATABASE_TYPES:
        raise ValueError(
            f"Invalid database_type '{value}'. "
            f"Must be one of: {', '.join(sorted(VALID_DATABASE_TYPES))}"
        )


@define(slots=False)
class DatabaseEntry:
    """Single database configuration entry."""

    database_name: str = field(validator=validators.min_len(1))
    database_type: DatabaseType = field(validator=_validate_database_type)
    database_url: str = field(validator=validators.min_len(1))
    default: bool = False
    migrations_dir: str | None = None
    model_paths: list[str] | None = None
    dev_database_type: DatabaseType | None = None
    dev_database_url: str | None = None
    overlap_models: bool = False


@define(slots=False)
class MultiDatabaseConfig:
    """Multi-database configuration container."""

    default: str
    databases: dict[str, DatabaseEntry]


# Global converter with detailed validation
_converter = cattrs.Converter(detailed_validation=True)
```

---

## 6) Validation Rules

Validation happens in two phases:

### Phase 1: Per-call validation (cattrs)

When `database_config(...)` is called, cattrs validates:

```python
def database_config(**kwargs) -> None:
    # Structure the kwargs into DatabaseEntry
    entry = _converter.structure(kwargs, DatabaseEntry)
    registry.add(entry)
```

cattrs catches:

- Missing required fields -> `MissingFieldError`
- Invalid type for field -> `StructuringFieldError` with field path
- Type coercion failures -> auto-convert or raise

Example cattrs error output:

```
cattrs.errors.ClassValidationError: While structuring DatabaseEntry
 +-+---------------- 1 ----------------
   | Structuring field 'database_type'
   | Invalid value 'postgres' for type DatabaseType. Expected one of: sqlite, postgresql, mysql, mariadb, clickhouse
   +------------------------------------
 +---------------- 2 ----------------
   | Structuring field 'database_name'
   | Missing field 'database_name'
   +------------------------------------
```

### Phase 2: Global uniqueness (manual)

After all entries collected, validate global constraints:

```python
def finalize_registry(entries: list[DatabaseEntry]) -> MultiDatabaseConfig:
    # Check exactly one default
    defaults = [e for e in entries if e.default]
    if len(defaults) != 1:
        raise ConfigurationError(
            f"Exactly one default=True required, found {len(defaults)}"
        )

    # Check unique names
    names = [e.database_name for e in entries]
    if len(set(names)) != len(names):
        dupes = [n for n in names if names.count(n) > 1]
        raise ConfigurationError(f"Duplicate database_name: {dupes}")

    # ... other uniqueness checks
```

## 6.1 Validation error mapping

cattrs exceptions transform to user-friendly messages:

```python
from cattrs import transform_error

def format_validation_error(exc: Exception, type_) -> str:
    """Custom error formatter for dbwarden config."""
    msgs = transform_error(exc)
    # e.g., "$.database_type: Invalid value 'postgres', expected one of: sqlite, postgresql..."
    return "; ".join(msgs)
```

---

## 7) Source Discovery and Resolution

Same as original design:

## 7.1 Resolution order

1. Recursively discover files named exactly `dbwarden.py`
2. If exactly one file found, use it
3. If more than one found, fail and print all paths
4. If none found, full scan Python files for `database_config(` occurrences
5. If exactly one candidate file found, use it
6. If multiple candidate files found, fail and print all paths
7. If no candidate found, try env var `DBWARDEN_CONFIG_MODULE`
8. If env var set, import module by dotted path
9. If env var absent, fail with setup guidance

## 7.2 Ignore directories

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

## 7.3 Performance note

Full content scan is acceptable for small/medium repos. For large monorepos:

```bash
export DBWARDEN_CONFIG_MODULE="myapp.settings.dbwarden_settings"
```

---

## 8) Runtime Loading Pipeline

```python
def load_runtime_config() -> MultiDatabaseConfig:
    source = resolve_source()
    registry.reset()
    resolver_cache.clear()  # clear per-process source cache for deterministic tests

    if source.kind == "file":
        import_module_from_path(source.path)
    else:
        import_module_by_name(source.module)

    entries = registry.entries()
    if not entries:
        raise ConfigurationError(
            "No database_config(...) call found. "
            "Add dbwarden init or set DBWARDEN_CONFIG_MODULE."
        )

    # Phase 2: Global validation
    cfg = finalize_registry(entries)

    # Dev-mode swap happens after validation and before returning:
    # if dev mode is enabled for selected DB, replace database_url/database_type
    # with dev_database_url/dev_database_type equivalents.
    return cfg
```

Cache invalidation contract:

- Resolver source cache is per-process.
- Cache must be cleared whenever `registry.reset()` runs.
- Test harnesses must call reset between tests to avoid stale-source false positives.

---

## 9) Final Normalized Internal Shape

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

---

## 10) `dbwarden init` Detailed Behavior

```bash
dbwarden init [path/to/file.py]
```

- No arg: target `./dbwarden.py`
- Arg provided: target exact path
- If parent directories missing: create them
- If file missing: create file

Ensure import:

```python
from dbwarden import database_config
```

Ensure scaffold:

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

Scaffold detection anchor rule:

- If file already contains any `database_config(` call, init treats scaffold as existing and does not append a new block.
- This remains true even if the existing call uses a non-default database name (for example `main` instead of `primary`).
- Import insertion remains independent: add import only if missing.

---

## 11) Settings CLI (Mutators)

Command group: `dbwarden settings ...`

Note on naming:

- Python API uses `database_config(...)`
- CLI uses `dbwarden settings ...` to avoid ambiguity while debugging/logging

Commands:

- `dbwarden settings show`
- `dbwarden settings default-database set <name>`
- `dbwarden settings database add <name> --type <type> --url <url> [--migrations-dir ...] [--model-path ...] [--dev-type ...] [--dev-url ...] [--overlap-models] [--default]`
- `dbwarden settings database remove <name>`
- `dbwarden settings database rename <old> <new>`
- `dbwarden settings database set-dev <name> --type <type> --url <url>`
- `dbwarden settings database clear-dev <name>`

Mutator lifecycle:

1. Resolve source
2. Parse and collect existing `database_config(...)` calls
3. Apply mutation to call set
4. Re-run full validation (cattrs + global)
5. Write deterministic updated calls back to file
6. Reload and verify config resolution

---

## 12) Error Contract

User-friendly error messages from cattrs:

| Error | Message |
|-------|---------|
| Multiple dbwarden.py files | `Multiple dbwarden.py files found. Keep exactly one.` |
| Multiple config call sites | `Multiple database_config(...) call sites found. Keep exactly one source or set DBWARDEN_CONFIG_MODULE.` |
| No config found | `No configuration found. Add database_config(...) call(s), create dbwarden.py with dbwarden init, or set DBWARDEN_CONFIG_MODULE.` |
| Missing required | `$.database_name: Missing field 'database_name'` |
| Invalid type | `$.database_type: Invalid value 'postgres', expected one of: sqlite, postgresql, mysql, mariadb, clickhouse` |
| Multiple defaults | `Exactly one default database required` |
| Duplicate name | `Duplicate database_name: 'primary'` |
| Duplicate URL | `Duplicate database_url: 'postgresql://...'` |
| Overlap without flag | `model_paths overlap detected: path 'models/shared' from 'analytics' is also defined in 'primary'; set overlap_models=True on 'primary' to allow foreign paths` |

Using `transform_error()` for clear field-path prefixes.

---

## 13) Implementation Steps

Execution checklist:

- [ ] Phase A: Schema & Converter
  - [ ] Add `attrs` + `cattrs` dependencies
  - [ ] Implement `DatabaseEntry` / `MultiDatabaseConfig`
  - [ ] Add converter and error formatting helper
  - [ ] Add unit tests for required fields and type coercion
- [ ] Phase B: Registry
  - [ ] Implement in-memory registry and `database_config(...)`
  - [ ] Implement finalize-time uniqueness/default/model overlap checks
  - [ ] Ensure cache invalidation is wired to `registry.reset()`
- [ ] Phase C: Source Resolver
  - [ ] Implement `dbwarden.py` discovery (strict one-file rule)
  - [ ] Implement full-scan fallback for `database_config(`
  - [ ] Implement `DBWARDEN_CONFIG_MODULE` fallback
  - [ ] Implement per-process source cache with invalidation rules
- [ ] Phase D: Runtime Integration
  - [ ] Replace TOML load path with runtime resolver + registry finalize
  - [ ] Keep existing command stack working (`migrate`, `status`, etc.)
  - [ ] Apply `--dev` URL/type swap before returning selected config
- [ ] Phase E: Init & Mutators
  - [ ] Rewrite `dbwarden init` to inject import + scaffold call
  - [ ] Implement idempotency anchor (`any database_config(` means scaffold exists)
  - [ ] Implement `dbwarden settings ...` group and mutators
- [ ] Phase F: Testing + Docs
  - [ ] Expand unit/integration tests for resolver and registry
  - [ ] Run full test suite and fix regressions
  - [ ] Update docs pages and publish

Test command matrix:

- [ ] `pytest tests/test_config.py`
- [ ] `pytest tests/test_commands.py`
- [ ] `pytest tests/test_cli_dev_mode.py`
- [ ] `pytest` (full suite)

### Phase A: Schema & Converter

1. Add `attrs` + `cattrs` to dependencies
2. Create `dbwarden/config/schema.py` with `DatabaseEntry`, `MultiDatabaseConfig`
3. Add custom validators for database_type
4. Set up global `_converter` with `detailed_validation=True`
5. Test schema validation

### Phase B: Registry

1. Create `dbwarden/config/registry.py`
2. Add `Registry` class: reset, add, entries, finalize
3. Integrate cattrs structure in `database_config()`

### Phase C: Source Resolver

Implementation unchanged from original design, with explicit cache behavior:

1. Add per-process source cache after first successful source resolution.
2. Cache key may be static per workspace process.
3. Invalidate cache when `registry.reset()` is called.
4. Tests must reset registry/cache between test cases.

### Phase D: Integration

1. Replace old config loader
2. Ensure migrate/rollback/status work

### Phase E: Init & Mutators

Implementation unchanged from original design.

---

## 14) Test Plan

Unit tests:

- Schema validation (cattrs errors)
- Cattrs type coercion
- Multi-database config finalization
- Global uniqueness checks

```python
# Example test
import pytest
from cattrs import StructuringError

def test_invalid_database_type():
    with pytest.raises(StructuringError) as exc_info:
        _converter.structure(
            {"database_name": "test", "database_type": "postgres", "database_url": "postgresql://..."},
            DatabaseEntry,
        )
    assert "database_type" in str(exc_info.value)
    assert "Invalid value" in str(exc_info.value)
```

Integration tests:

- Full loading pipeline
- Error formatting
- CLI commands

---

## 15) Comparison: Original vs. cattrs Alternative

| Aspect | Original (manual) | cattrs Alt |
|--------|--------------|-----------|
| **Dependencies** | None | attrs + cattrs |
| **Validation** | Manual if/raise per field | attrs validators |
| **Errors** | Custom strings | cattrs with paths |
| **Type coercion** | Manual | Built-in |
| **Code size** | Longer | Shorter |
| **Extensibility** | Manual hooks | Register hooks |
| **Learning curve** | None | attrs/cattrs |

---

## 16) Acceptance Criteria

1. DBWarden runs without TOML anywhere.
2. Config resolves using: `dbwarden.py` -> full scan -> env fallback.
3. cattrs validates per-call fields with rich errors.
4. Global uniqueness rules enforced at finalize.
5. `database_config()` uses attrs + cattrs under the hood.
6. Multiple databases supported.
7. Exactly one default enforced.
8. `dbwarden init` creates valid scaffold.
9. Settings CLI mutators work.
10. Documentation updated.
