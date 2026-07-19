---
description: DBWarden sandbox mechanisms: migration validation in temporary databases
  and config file security isolation.
---

# Sandbox

DBWarden provides two sandbox mechanisms that protect your production data from unintended changes.

## Migration Sandbox

The `--sandbox` flag applies pending migrations to a temporary database and reports results without touching the real target.

```bash
dbwarden migrate --sandbox --database primary
```

When you run with `--sandbox`, DBWarden creates a fresh sandbox instance (SQLite by default, or a Docker-backed database when the `[sandbox]` extra is installed), applies all pending migrations, and reports success or failure. The sandbox is then torn down. Nothing touches the production database.

### Use Cases

**Validating generated SQL before real deployment.** After running `make-migrations`, validate the SQL against a temporary database to catch syntax errors, missing columns, or type mismatches.

```bash
dbwarden make-migrations "add reporting table"
dbwarden migrate --sandbox --database primary
```

**CI gates.** Run the sandbox check in pull request pipelines to ensure every migration compiles and applies cleanly.

```yaml
sandbox-check:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - uses: actions/checkout@v4
    - run: uv add -e ".[migrations,testcontainers]"
    - name: Apply migrations to sandbox
      run: dbwarden migrate --sandbox --database primary
```

The sandbox starts a fresh database, applies all pending migrations, reports results, and tears down. It never touches the real database.

**Combined with dry-run.** Chain `--dry-run` (preview SQL without any database access) before `--sandbox` for a two-phase validation.

```bash
dbwarden migrate --dry-run --database primary
dbwarden migrate --sandbox --database primary
```

### Behavior

- Sandbox migrations follow the same migration ordering and dependency resolution as real migrations.
- Schema snapshots are not written during sandbox runs.
- The sandbox backend defaults to SQLite when the `[sandbox]` extra is not installed.
- With `uv add "dbwarden[sandbox]"`, the sandbox can spin up Docker containers matching your production database type.

## Config Security Sandbox

DBWarden applies import restrictions to config files loaded from isolated locations. This prevents accidental escalation of file-read access to arbitrary code execution.

### How It Works

Config files are loaded in one of two modes:

| Mode | Import behavior | Applies to |
|------|----------------|------------|
| Isolated | Sandboxed: only `dbwarden.*` imports allowed | Top-level `dbwarden.py`; any full-scan-discovered file at the project root |
| In-package | Normal Python import | Full-scan-discovered files inside subdirectories; `DBWARDEN_CONFIG_MODULE` modules |

An isolated config file runs in a sandbox where only `dbwarden` and its submodules can be imported. An in-package config file is imported as a normal Python module, with full access to project-level imports.

### Path Validation

Path traversal blocking applies to all file-based sources regardless of mode. DBWarden validates that config file paths stay within the project root.

### Debugging

To disable the sandbox for isolated files during development:

```bash
DBWARDEN_DISABLE_SANDBOX=1 dbwarden status
```

Disabling the sandbox removes import restrictions for isolated config files. Keep it enabled in production.
