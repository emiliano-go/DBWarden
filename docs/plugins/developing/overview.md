---
description: Overview of DBWarden plugin development.
---

# Plugin Development Overview

A DBWarden plugin is a Python package with one entry point in the `dbwarden.plugins` group. The entry point points to a `setup(registry)` callable that registers hooks or object handlers.

```toml
[project.entry-points."dbwarden.plugins"]
example = "dbwarden_example:setup"
```

`setup` is defined in the package's `__init__.py`, so the entry point is `dbwarden_example:setup` (not `...plugin:setup`). Hook functions live at module top level, and heavy or DBWarden-specific imports go inside the function body so importing the package stays side-effect-free:

```python
# src/dbwarden_example/__init__.py
import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_model_module(path: Path, base_dir: Path) -> Any:
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)  # deferred/lazy work
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def setup(registrar) -> None:
    registrar.register("load_model_module", load_model_module)
```

## Two Kinds Of Plugin

- **[Value plugins](value-plugins.md)** supply a value at a named hook point: session factories, FastAPI routes, lifespans, seed commands, module loaders. Registered with `registry.register(name, callable)`.
- **[Object plugins](object-plugins.md)** add a database object type to the schema diff pipeline: extensions, roles, grants, triggers, types. Registered with `registry.register_object_handler(handler)`.

A single package may register both.

## Lifecycle

1. DBWarden discovers entry-point metadata (name, version, value) without importing your code.
2. DBWarden classifies the distribution into a trust tier by name.
3. If trust rules allow loading, DBWarden imports the entry point and calls `setup(registry)`.
4. `setup(registry)` registers value hooks and/or object handlers.

The `registry` argument is a `PluginRegistrar` bound to your distribution name, so DBWarden attributes every hook to your plugin (used for conflict reporting and `plugin list`).

## Naming Conventions

All plugins are distributed as `dbwarden-<name>`. The import package and entry-point key derive from the distribution name: `slug = distribution.removeprefix("dbwarden-").replace("-", "_")`, then import package = `dbwarden_<slug>` and entry key = `<slug>`.

| Role | Convention | Example |
|------|------------|---------|
| PyPI project | `dbwarden-<name>` | `dbwarden-audit` |
| Import package | `dbwarden_<slug>` | `dbwarden_audit` |
| Entry-point key | `<slug>` | `audit` |

The `dbwarden-` prefix is shared by every plugin; a plugin's trust tier comes from the curated Official/Approved lists in core, not from its name. See [publishing](publishing.md#naming) for the full rule.

## Project Structure

Start from the [`dbwarden-plugin-template`](https://github.com/dbwarden-org/dbwarden-plugin-template) GitHub template (see [publishing](publishing.md#starting-from-the-template)):

```text
dbwarden-example/
├── pyproject.toml
├── src/dbwarden_example/
│   ├── __init__.py        # hook functions + setup(registrar)
│   └── handler.py         # object plugins only
├── tests/
│   └── test_example_plugin.py
├── README.md
└── LICENSE
```

`setup(registrar)` goes at the bottom of `__init__.py`. There is no `plugin.py`.

## The Core Contract

- Depend on the **public** `dbwarden.plugin` API (`PluginRegistrar`) and, for object plugins, the public types re-exported from `dbwarden.engine.core` (`Anchor`, `OrderingConstraint`, `Op`, `MigrationStatement`, `RunPhase`).
- **Do not** import private internals such as `dbwarden.commands.*`, `dbwarden.database.*`, or non-exported `dbwarden.engine.*` symbols. Only official extracted-from-core packages do that, and only against a pinned core version.
- Use public **ordering anchors**, never private `StatementOrder` integers, those are renumbered freely.

## Rules

- **No import-time side effects.** Registering a hook must happen inside `setup()`, never at module import. Importing your package should register nothing.
- **Defer heavy imports to call time.** Value hooks import their DBWarden internals (and optional deps like FastAPI or drivers) inside the hook function body; object plugins import their `handler` module inside `setup()`. That way merely importing the package pulls in nothing heavy.
- Match documented hook signatures exactly; see the [hook catalog](../reference/hook-catalog.md).
