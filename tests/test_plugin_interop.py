"""Interactions between real plugins installed side by side.

Everything else about plugins is tested with stand-ins. These tests use the
actual official plugin packages, because the failures they cover only appear
when two independently written plugins meet in one process: a claimed object
type, a single-value hook claimed twice, ordering across packages.

Skipped when the plugins are not installed, which is the normal case in core's
own environment. The ecosystem workflow (scripts/ecosystem-check.py) installs
them, and so does any environment built for cross-plugin work.
"""
from __future__ import annotations

import importlib

import pytest

from dbwarden.plugin import (
    HookConflictError,
    HookRegistry,
    ObjectHandlerConflictError,
    ObjectPluginRegistry,
    PluginRegistrar,
)


def _plugin(package: str):
    module = pytest.importorskip(
        package, reason=f"{package} is not installed in this environment"
    )
    return module


@pytest.fixture(autouse=True)
def clean_registries():
    HookRegistry.clear()
    ObjectPluginRegistry.clear()
    yield
    HookRegistry.clear()
    ObjectPluginRegistry.clear()


# --- object type collisions ------------------------------------------------

def test_official_object_plugins_claim_disjoint_types() -> None:
    """No two official plugins may claim the same object type.

    They are loaded together in any PostgreSQL project, so an overlap is not a
    conflict a user could resolve: it would simply fail at startup.
    """
    packages = [
        "dbwarden_ch_rbac",
        "dbwarden_pgsql_rbac",
        "dbwarden_pgsql_types",
        "dbwarden_pgsql_extensions",
    ]
    installed = []
    for package in packages:
        try:
            installed.append((package, importlib.import_module(package)))
        except ImportError:
            continue
    if len(installed) < 2:
        pytest.skip("needs at least two official object plugins installed")

    seen: dict[str, str] = {}
    for package, module in installed:
        for handler_class in module.HANDLER_CLASSES:
            object_type = handler_class.object_type
            assert object_type not in seen, (
                f"'{object_type}' claimed by both {seen.get(object_type)} and {package}"
            )
            seen[object_type] = package


def test_two_plugins_claiming_one_object_type_conflict() -> None:
    """The collision above is caught at registration, not silently resolved."""
    module = _plugin("dbwarden_pgsql_types")
    handler_class = module.HANDLER_CLASSES[0]

    PluginRegistrar("dbwarden-pgsql-types").register_object_handler(handler_class())

    with pytest.raises(ObjectHandlerConflictError) as excinfo:
        PluginRegistrar("dbwarden-impostor").register_object_handler(handler_class())

    assert handler_class.object_type in str(excinfo.value)


def test_installing_every_official_object_plugin_registers_cleanly() -> None:
    """All of them together, the way a real project loads them."""
    modules = []
    for package in (
        "dbwarden_ch_rbac",
        "dbwarden_pgsql_rbac",
        "dbwarden_pgsql_types",
        "dbwarden_pgsql_extensions",
    ):
        try:
            modules.append((package, importlib.import_module(package)))
        except ImportError:
            continue
    if len(modules) < 2:
        pytest.skip("needs at least two official object plugins installed")

    expected = 0
    for package, module in modules:
        module.setup(PluginRegistrar(package.replace("_", "-")))
        expected += len(module.HANDLER_CLASSES)

    assert len(ObjectPluginRegistry.handlers()) == expected


def test_all_registered_handlers_order_without_a_cycle() -> None:
    """Ordering constraints must stay satisfiable once plugins are combined.

    Each plugin checks its own constraints in isolation. A cycle can still be
    introduced by two plugins that each anchor against the other's object type.
    """
    from dbwarden.engine.core.ordering import order_handlers

    modules = []
    for package in (
        "dbwarden_ch_rbac",
        "dbwarden_pgsql_rbac",
        "dbwarden_pgsql_types",
        "dbwarden_pgsql_extensions",
    ):
        try:
            modules.append(importlib.import_module(package))
        except ImportError:
            continue
    if len(modules) < 2:
        pytest.skip("needs at least two official object plugins installed")

    for module in modules:
        module.setup(PluginRegistrar(module.__name__.replace("_", "-")))

    handlers = {
        object_type: registration.handler
        for object_type, registration in ObjectPluginRegistry.handlers().items()
    }
    ordered = order_handlers(handlers)

    assert len(ordered) == len(handlers)


# --- value hook collisions -------------------------------------------------

def test_two_plugins_claiming_one_single_value_hook_conflict() -> None:
    """Single-value hooks are first-come; the clash surfaces when core calls."""
    seeds = _plugin("dbwarden_seeds")

    seeds.setup(PluginRegistrar("dbwarden-seeds"))
    PluginRegistrar("dbwarden-impostor").register("seed_apply", lambda **kw: None)

    with pytest.raises(HookConflictError) as excinfo:
        HookRegistry.execute_single("seed_apply")

    message = str(excinfo.value)
    assert "dbwarden-seeds" in message
    assert "dbwarden-impostor" in message


def test_seeds_and_fastapi_register_disjoint_hooks() -> None:
    """Two value plugins commonly installed together must not collide."""
    seeds = _plugin("dbwarden_seeds")
    fastapi_plugin = _plugin("dbwarden_fastapi")

    seeds.setup(PluginRegistrar("dbwarden-seeds"))
    seeds_hooks = set(HookRegistry.hooks())

    fastapi_plugin.setup(PluginRegistrar("dbwarden-fastapi"))
    combined = HookRegistry.hooks()

    for hook_name, entries in combined.items():
        providers = [plugin_name for plugin_name, _ in entries]
        if hook_name in seeds_hooks:
            assert providers == ["dbwarden-seeds"], (
                f"'{hook_name}' gained a second provider: {providers}"
            )
