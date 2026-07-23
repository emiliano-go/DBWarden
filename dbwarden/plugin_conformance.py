"""Conformance harness for the DBWarden Verified (Approved) plugin standard.

Plugin authors call these assertions from their own pytest suite. Each function
raises ``AssertionError`` (or ``ConformanceError``) with an explanatory message
on failure, so one ``def test_...()`` per check reads cleanly. None of this
imports pytest, so it works in any test runner.

See docs/plugins/developing/approved-standard.md for the full standard.
"""
from __future__ import annotations

import ast
import importlib
import importlib.metadata
import importlib.util
import inspect
import tomllib
from pathlib import Path
from typing import Any, Callable

from dbwarden.engine.core import MigrationStatement, Op
from dbwarden.engine.core.ordering import OrderingConstraint, OrderingError, apply_public_ordering, order_handlers, validate_ordering
from dbwarden.plugin import (
    HOOK_CALL_SPECS,
    KNOWN_VALUE_HOOKS,
    HookRegistry,
    ObjectPluginRegistry,
    PLUGIN_GROUP,
    PluginRegistrar,
)

PLUGIN_ENTRY_GROUP = PLUGIN_GROUP

# A plugin may import only the public API surface. `dbwarden.engine.core`
# re-exports the public object-handler types; everything else under
# `dbwarden.<subpackage>` is internal.
ALLOWED_IMPORT_PREFIXES: tuple[str, ...] = (
    "dbwarden.plugin",
    "dbwarden.exceptions",
    "dbwarden.engine.core",
)


class ConformanceError(AssertionError):
    """Raised when a plugin violates the Verified standard."""


class RecordingRegistrar:
    """Stand-in for ``PluginRegistrar`` that records registrations."""

    def __init__(self, plugin: str = "plugin-under-test") -> None:
        self.plugin = plugin
        self.hooks: dict[str, Callable[..., Any]] = {}
        self.object_handlers: list[Any] = []

    def register(self, hook_name: str, fn: Callable[..., Any]) -> None:
        self.hooks[hook_name] = fn

    def register_object_handler(self, handler: Any) -> None:
        self.object_handlers.append(handler)


def _collect(setup: Callable[[Any], None], plugin: str) -> RecordingRegistrar:
    registrar = RecordingRegistrar(plugin)
    setup(registrar)
    return registrar


def _package_source_files(package: str) -> list[Path]:
    spec = importlib.util.find_spec(package)
    if spec is None:
        raise ConformanceError(f"Package '{package}' is not importable.")
    locations = list(spec.submodule_search_locations or [])
    if locations:
        return [p for loc in locations for p in Path(loc).rglob("*.py")]
    if spec.origin and spec.origin.endswith(".py"):
        return [Path(spec.origin)]
    return []


# --- 1. entry point --------------------------------------------------------

def assert_entry_point_declared(
    distribution: str | None = None,
    *,
    pyproject_path: str | Path = "pyproject.toml",
) -> None:
    """The package declares a resolvable ``dbwarden.plugins`` entry point.

    Reads the entry point from ``pyproject.toml`` (so it works without an
    installed distribution) and confirms the ``module:attr`` target imports to
    a callable. When ``distribution`` is given and installed, the entry point is
    also cross-checked via ``importlib.metadata``.
    """
    path = Path(pyproject_path)
    if not path.exists():
        raise ConformanceError(f"No pyproject.toml at {path}.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = (
        data.get("project", {})
        .get("entry-points", {})
        .get(PLUGIN_ENTRY_GROUP, {})
    )
    if not entries:
        raise ConformanceError(
            f'pyproject.toml declares no [project.entry-points."{PLUGIN_ENTRY_GROUP}"] entry point.'
        )
    for key, target in entries.items():
        module_name, _, attr = str(target).partition(":")
        if not module_name or not attr:
            raise ConformanceError(f"Entry point '{key}' target '{target}' is not 'module:attr'.")
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 - surface any import failure
            raise ConformanceError(f"Entry point '{key}' module '{module_name}' failed to import: {exc}")
        fn = getattr(module, attr, None)
        if not callable(fn):
            raise ConformanceError(f"Entry point '{key}' target '{target}' is not callable.")

    if distribution is not None:
        eps = importlib.metadata.entry_points(group=PLUGIN_ENTRY_GROUP)
        names = {ep.name for ep in eps}
        if not names:
            return  # not installed as a distribution; pyproject check already passed
        if not (set(entries) & names):
            raise ConformanceError(
                f"Declared entry points {sorted(entries)} not found in installed metadata for '{distribution}'."
            )


# --- 2. no import-time side effects ---------------------------------------

def assert_import_has_no_side_effects(package: str) -> None:
    """Importing the package registers nothing and mutates no plugin state."""
    HookRegistry.clear()
    ObjectPluginRegistry.clear()
    module = importlib.import_module(package)
    importlib.reload(module)
    for submodule in ("plugin", "handler"):
        name = f"{package}.{submodule}"
        if importlib.util.find_spec(name) is not None:
            importlib.reload(importlib.import_module(name))
    if HookRegistry.hooks():
        raise ConformanceError(
            f"Importing '{package}' registered hooks {sorted(HookRegistry.hooks())}; "
            "registration must happen only inside setup()."
        )
    if ObjectPluginRegistry.handlers():
        raise ConformanceError(
            f"Importing '{package}' registered object handlers {sorted(ObjectPluginRegistry.handlers())}."
        )


# --- 3. setup registers hooks ---------------------------------------------

def assert_setup_registers(
    setup: Callable[[Any], None],
    *,
    plugin: str = "plugin-under-test",
    value_hooks: tuple[str, ...] = (),
    object_types: tuple[str, ...] = (),
) -> RecordingRegistrar:
    """Calling ``setup`` registers the declared hooks / object handlers."""
    registrar = _collect(setup, plugin)
    if not registrar.hooks and not registrar.object_handlers:
        raise ConformanceError("setup() registered nothing.")
    missing_hooks = set(value_hooks) - set(registrar.hooks)
    if missing_hooks:
        raise ConformanceError(f"setup() did not register value hooks: {sorted(missing_hooks)}.")
    got_types = {getattr(h, "object_type", None) for h in registrar.object_handlers}
    missing_types = set(object_types) - got_types
    if missing_types:
        raise ConformanceError(f"setup() did not register object types: {sorted(missing_types)}.")
    return registrar


# --- 4. hook signature compliance -----------------------------------------

def assert_hook_signatures(
    setup: Callable[[Any], None],
    *,
    plugin: str = "plugin-under-test",
) -> None:
    """Each registered value hook accepts the arguments core calls it with."""
    registrar = _collect(setup, plugin)
    for name, fn in registrar.hooks.items():
        if name not in HOOK_CALL_SPECS:
            continue
        args, kwargs = HOOK_CALL_SPECS[name]
        try:
            inspect.signature(fn).bind(*args, **kwargs)
        except (TypeError, ValueError) as exc:
            raise ConformanceError(
                f"Hook '{name}' signature is incompatible with how core calls it: {exc}"
            )


# --- 5. no core internals imported ----------------------------------------

def _import_is_allowed(module: str) -> bool:
    if not module.startswith("dbwarden"):
        return True
    if module == "dbwarden":
        return True
    return any(module == p or module.startswith(p + ".") for p in ALLOWED_IMPORT_PREFIXES)


def assert_no_core_internals_imported(package: str) -> None:
    """The plugin imports only DBWarden's public API surface."""
    violations: list[str] = []
    for file in _package_source_files(package):
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            for module in modules:
                if not _import_is_allowed(module):
                    violations.append(f"{file.name}:{node.lineno} imports '{module}'")
    if violations:
        raise ConformanceError(
            "Plugin imports non-public DBWarden internals (allowed: "
            f"{', '.join(ALLOWED_IMPORT_PREFIXES)}):\n  " + "\n  ".join(violations)
        )


# --- 6. object handler conformance (object plugins) -----------------------

def assert_object_handler_conformance(
    handler: Any,
    *,
    snapshot: dict[str, Any] | None = None,
    config: Any = None,
    model_spec: dict[str, Any] | None = None,
) -> None:
    """The handler plugs into extract -> canonicalize -> diff -> emit."""
    object_type = getattr(handler, "object_type", None)
    if not isinstance(object_type, str) or not object_type:
        raise ConformanceError("Object handler must define a non-empty string object_type.")
    apply_public_ordering(handler)  # sets statement_order from ordering anchors

    snap_spec = handler.extract(snapshot or {})
    if not isinstance(snap_spec, dict):
        raise ConformanceError("extract() must return a dict.")

    from_config = handler.model_spec_from_config(config) if config is not None else {}
    from_tables = handler.model_spec_from_tables([])
    if not isinstance(from_config, dict):
        raise ConformanceError("model_spec_from_config() must return a dict.")
    if not isinstance(from_tables, dict):
        raise ConformanceError("model_spec_from_tables() must return a dict.")
    # Pick a non-empty desired spec so diff() and emit() are actually exercised.
    desired = model_spec if model_spec is not None else (from_config or from_tables)

    canon_snap = handler.canonicalize(snap_spec)
    canon_model = handler.canonicalize(desired)
    if not isinstance(canon_snap, dict) or not isinstance(canon_model, dict):
        raise ConformanceError("canonicalize() must return a dict.")

    result = handler.diff(canon_snap, canon_model)
    if not (isinstance(result, tuple) and len(result) == 2):
        raise ConformanceError("diff() must return a (upgrade_ops, rollback_ops) tuple.")
    upgrade_ops, rollback_ops = result
    for ops in (upgrade_ops, rollback_ops):
        if not isinstance(ops, list) or not all(isinstance(op, Op) for op in ops):
            raise ConformanceError("diff() must return lists of Op.")

    for op in upgrade_ops:
        statements = handler.emit(op)
        if not isinstance(statements, list) or not all(isinstance(s, MigrationStatement) for s in statements):
            raise ConformanceError("emit() must return a list of MigrationStatement.")
        for statement in statements:
            if not isinstance(statement.upgrade_sql, str) or not isinstance(statement.rollback_sql, str):
                raise ConformanceError("emit() statements must carry string SQL.")


# --- 7. ordering constraint satisfiable (object plugins) ------------------

def assert_ordering_constraint_satisfiable(handler: Any) -> None:
    """The handler's OrderingConstraint is not statically impossible."""
    ordering = getattr(handler, "ordering", None)
    if ordering is None:
        return
    if not isinstance(ordering, OrderingConstraint):
        raise ConformanceError("ordering must be an OrderingConstraint.")
    try:
        validate_ordering(ordering)
        order_handlers({handler.object_type: handler})
    except OrderingError as exc:
        raise ConformanceError(f"Ordering constraint is unsatisfiable: {exc}")


# --- 8. idempotent setup (recommended) ------------------------------------

def assert_idempotent_setup(
    setup: Callable[[Any], None],
    *,
    plugin: str = "plugin-under-test",
) -> None:
    """Calling setup() twice does not raise or add new hook/handler names."""
    HookRegistry.clear()
    ObjectPluginRegistry.clear()
    registrar = PluginRegistrar(plugin)
    setup(registrar)
    hooks_after_first = set(HookRegistry.hooks())
    objects_after_first = set(ObjectPluginRegistry.handlers())
    try:
        setup(registrar)
    except Exception as exc:  # noqa: BLE001 - a second setup must not raise
        raise ConformanceError(f"Calling setup() twice raised {type(exc).__name__}: {exc}")
    if set(HookRegistry.hooks()) != hooks_after_first:
        raise ConformanceError("Second setup() changed the set of registered hook names.")
    if set(ObjectPluginRegistry.handlers()) != objects_after_first:
        raise ConformanceError("Second setup() changed the set of registered object types.")
