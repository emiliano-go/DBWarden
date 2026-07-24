from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from dbwarden.engine.core import Anchor, MigrationStatement, Op, OrderingConstraint, RunPhase
from dbwarden.plugin import HookRegistry, ObjectPluginRegistry
from dbwarden.plugin_conformance import (
    ConformanceError,
    assert_entry_point_declared,
    assert_hook_signatures,
    assert_idempotent_setup,
    assert_import_has_no_side_effects,
    assert_core_imports_resolve,
    assert_object_handler_conformance,
    assert_ordering_constraint_satisfiable,
    assert_setup_registers,
)


def test_hook_call_specs_cover_all_known_hooks():
    from dbwarden.plugin import HOOK_CALL_SPECS, KNOWN_VALUE_HOOKS

    assert set(HOOK_CALL_SPECS) == set(KNOWN_VALUE_HOOKS)


@pytest.fixture(autouse=True)
def _clean_state():
    HookRegistry.clear()
    ObjectPluginRegistry.clear()
    yield
    HookRegistry.clear()
    ObjectPluginRegistry.clear()


@pytest.fixture
def make_module(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    created: list[str] = []

    def _make(name: str, source: str, *, package: bool = False) -> str:
        if package:
            pkg = tmp_path / name
            pkg.mkdir()
            (pkg / "__init__.py").write_text(source, encoding="utf-8")
        else:
            (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
        created.append(name)
        importlib.invalidate_caches()
        return name

    yield _make

    for name in created:
        sys.modules.pop(name, None)


# --- fixtures: good/bad plugin building blocks -----------------------------

def _good_value_setup(registrar) -> None:
    def load_model_module(path, base_dir):
        return None

    registrar.register("load_model_module", load_model_module)


class _GoodHandler:
    object_type = "widget"
    op_types = ("create_widget", "drop_widget")
    run_phase = RunPhase.DIFF
    ordering = OrderingConstraint(after=(Anchor.AFTER_TABLES,))

    def extract(self, snapshot):
        return dict(snapshot.get("widgets", {}) or {})

    def model_spec_from_config(self, config):
        return {}

    def model_spec_from_tables(self, model_tables):
        return {"w1": {}}

    def canonicalize(self, spec):
        return dict(sorted((spec or {}).items()))

    def diff(self, snap_spec, model_spec):
        ups = [Op("create_widget", {"name": n}, {"name": n}) for n in sorted(set(model_spec) - set(snap_spec))]
        return ups, []

    def emit(self, op, db_name=None, **kwargs):
        name = op.upgrade_attrs["name"]
        return [MigrationStatement(order=self.statement_order, upgrade_sql=f"CREATE {name}", rollback_sql=f"DROP {name}")]


# --- 3. setup registers ----------------------------------------------------

def test_assert_setup_registers_passes():
    assert_setup_registers(_good_value_setup, value_hooks=("load_model_module",))


def test_assert_setup_registers_missing_hook_fails():
    with pytest.raises(ConformanceError, match="did not register value hooks"):
        assert_setup_registers(_good_value_setup, value_hooks=("session_factory",))


def test_assert_setup_registers_nothing_fails():
    with pytest.raises(ConformanceError, match="registered nothing"):
        assert_setup_registers(lambda registrar: None)


# --- 4. hook signature compliance -----------------------------------------

def test_assert_hook_signatures_passes():
    assert_hook_signatures(_good_value_setup)


def test_assert_hook_signatures_bad_signature_fails():
    def bad_setup(registrar):
        registrar.register("session_factory", lambda db: None)  # missing dev kwarg

    with pytest.raises(ConformanceError, match="signature is incompatible"):
        assert_hook_signatures(bad_setup)


def test_assert_hook_signatures_accepts_documented_session_factory():
    def setup(registrar):
        registrar.register("session_factory", lambda database=None, *, dev=False: None)

    assert_hook_signatures(setup)


# --- 6. object handler conformance ----------------------------------------

def test_assert_object_handler_conformance_passes():
    assert_object_handler_conformance(_GoodHandler(), snapshot={"widgets": {}})


def test_assert_object_handler_conformance_bad_extract_fails():
    class Bad(_GoodHandler):
        def extract(self, snapshot):
            return []  # not a dict

    with pytest.raises(ConformanceError, match="extract"):
        assert_object_handler_conformance(Bad())


def test_assert_object_handler_conformance_bad_emit_fails():
    class Bad(_GoodHandler):
        def emit(self, op, db_name=None, **kwargs):
            return ["not a MigrationStatement"]

    with pytest.raises(ConformanceError, match="emit"):
        assert_object_handler_conformance(Bad())


def test_assert_object_handler_missing_object_type_fails():
    class Bad(_GoodHandler):
        object_type = ""

    with pytest.raises(ConformanceError, match="object_type"):
        assert_object_handler_conformance(Bad())


# --- 7. ordering satisfiable -----------------------------------------------

def test_assert_ordering_satisfiable_passes():
    assert_ordering_constraint_satisfiable(_GoodHandler())


def test_assert_ordering_impossible_pair_fails():
    class Bad(_GoodHandler):
        ordering = OrderingConstraint(after=(Anchor.POSTAMBLE,), before=(Anchor.PREAMBLE,))

    with pytest.raises(ConformanceError, match="unsatisfiable"):
        assert_ordering_constraint_satisfiable(Bad())


def test_assert_ordering_none_passes():
    class NoOrdering:
        object_type = "x"

    assert_ordering_constraint_satisfiable(NoOrdering())


# --- 8. idempotent setup ---------------------------------------------------

def test_assert_idempotent_setup_passes():
    assert_idempotent_setup(_good_value_setup)


def test_assert_idempotent_setup_object_plugin_passes():
    def setup(registrar):
        registrar.register_object_handler(_GoodHandler())

    assert_idempotent_setup(setup)


# --- 1. entry point (module-backed) ---------------------------------------

def test_assert_entry_point_declared_passes(make_module, tmp_path):
    make_module("epmod", "def setup(registrar):\n    pass\n")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project.entry-points."dbwarden.plugins"]\nexample = "epmod:setup"\n',
        encoding="utf-8",
    )
    assert_entry_point_declared(pyproject_path=pyproject)


def test_assert_entry_point_missing_table_fails(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "dbwarden-x"\n', encoding="utf-8")
    with pytest.raises(ConformanceError, match="no .* entry point"):
        assert_entry_point_declared(pyproject_path=pyproject)


def test_assert_entry_point_uncallable_target_fails(make_module, tmp_path):
    make_module("epmod2", "setup = 123\n")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project.entry-points."dbwarden.plugins"]\nexample = "epmod2:setup"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConformanceError, match="not callable"):
        assert_entry_point_declared(pyproject_path=pyproject)


# --- 2. no import side effects ---------------------------------------------

def test_assert_import_no_side_effects_passes(make_module):
    name = make_module(
        "clean_plugin",
        "def setup(registrar):\n    registrar.register('load_model_module', lambda p, b: None)\n",
        package=True,
    )
    assert_import_has_no_side_effects(name)


def test_assert_import_side_effect_fails(make_module):
    name = make_module(
        "dirty_plugin",
        "from dbwarden.plugin import HookRegistry\n"
        "HookRegistry.register('load_model_module', lambda p, b: None, plugin='dirty')\n"
        "def setup(registrar):\n    pass\n",
        package=True,
    )
    with pytest.raises(ConformanceError, match="registered hooks"):
        assert_import_has_no_side_effects(name)


# --- 5. core imports resolve ----------------------------------------------

def test_assert_core_imports_resolve_passes_on_stable_api(make_module):
    name = make_module(
        "public_plugin",
        "from dbwarden.plugin import PluginRegistrar\n"
        "from dbwarden.engine.core import Op\n"
        "def setup(registrar):\n    pass\n",
        package=True,
    )
    assert_core_imports_resolve(name)


def test_assert_core_imports_resolve_allows_deeper_core_imports(make_module):
    name = make_module(
        "internal_plugin",
        "import dbwarden.engine.snapshot\n"
        "def setup(registrar):\n    pass\n",
        package=True,
    )
    assert_core_imports_resolve(name)


def test_assert_core_imports_resolve_fails_on_missing_module(make_module):
    name = make_module(
        "stale_plugin",
        "import dbwarden.engine.no_such_module\n"
        "def setup(registrar):\n    pass\n",
        package=True,
    )
    with pytest.raises(ConformanceError, match="does not\\s+provide|not found"):
        assert_core_imports_resolve(name)


def test_core_imports_outside_stable_api_reports_without_failing(make_module):
    from dbwarden.plugin_conformance import core_imports_outside_stable_api

    name = make_module(
        "mixed_plugin",
        "from dbwarden.engine.core import Op\n"
        "import dbwarden.engine.snapshot\n"
        "def setup(registrar):\n    pass\n",
        package=True,
    )
    reported = core_imports_outside_stable_api(name)
    assert len(reported) == 1
    assert "dbwarden.engine.snapshot" in reported[0]
