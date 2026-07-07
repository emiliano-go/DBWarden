"""Golden tests and contract tests for Phase 0 pg_registry module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry import EnumHandler
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
    _assemble_migration,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeColumn:
    name: str = "col"
    pg_meta: dict[str, Any] = field(default_factory=dict)

@dataclass
class FakeTable:
    name: str = "t"
    columns: list[FakeColumn] = field(default_factory=list)


def _make_model_table(cols: list[dict[str, Any]]) -> list[FakeTable]:
    return [
        FakeTable(
            columns=[
                FakeColumn(name=c.get("name", "col"), pg_meta=c.get("pg_meta", {}))
                for c in cols
            ],
        )
    ]


def _model_enum_values(model_tables: list[FakeTable]) -> dict[str, list[str]]:
    """Inline extraction — exact copy of snapshot.py:3395-3396."""
    model_enum_values: dict[str, list[str]] = {}
    for table in model_tables:
        for col in table.columns:
            pg_type = col.pg_meta.get("pg_type", {})
            if pg_type.get("kind") == "enum":
                type_name: str = pg_type.get("type_name", "")
                if type_name:
                    model_enum_values[type_name] = pg_type.get("values", [])
    return model_enum_values


def _inline_enum_diff(
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inline diff — exact copy of snapshot.py:3393-3426."""
    snap_enums: dict[str, list[str]] = snapshot.get("enums", {})
    model_enum_values = _model_enum_values(model_tables)

    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    for enum_name, snap_values in snap_enums.items():
        to_values = model_enum_values.get(enum_name)
        if to_values is None:
            continue
        snap_set = set(snap_values)
        new_values = [v for v in to_values if v not in snap_set]
        if new_values:
            pos_map = {v: i for i, v in enumerate(to_values)}
            for v in new_values:
                idx = pos_map[v]
                after = to_values[idx - 1] if idx > 0 else None
                upgrade_ops.append({
                    "type": "alter_enum_add_value",
                    "enum_name": enum_name,
                    "value": v,
                    "after": after,
                })
                rollback_ops.append({
                    "type": "alter_enum_add_value",
                    "enum_name": enum_name,
                    "value": v,
                    "revert": True,
                    "after": after,
                })

    for enum_name, curr_values in model_enum_values.items():
        if enum_name not in snap_enums:
            upgrade_ops.append({"type": "create_type", "enum_name": enum_name, "values": curr_values})
            rollback_ops.insert(0, {"type": "drop_type", "enum_name": enum_name, "values": curr_values})

    return upgrade_ops, rollback_ops


def _inline_enum_emit(
    ops: list[dict[str, Any]],
) -> list[MigrationStatement]:
    """Inline emit — exact copy of snapshot.py:4403-4441."""
    statements: list[MigrationStatement] = []
    for op in ops:
        if op.get("type") == "alter_enum_add_value":
            enum_name = op["enum_name"]
            value = op["value"]
            after = op.get("after")
            after_clause = f" AFTER {after!r}" if after else ""
            if op.get("revert"):
                up = f"-- Revert: {value} was added to enum {enum_name}"
                rb = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
            else:
                up = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
                rb = f"-- Revert: {value} was added to enum {enum_name}"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op.get("type") == "create_type":
            enum_name = op["enum_name"]
            values_sql = ", ".join(repr(v) for v in op.get("values", []))
            up = f"CREATE TYPE {enum_name} AS ENUM ({values_sql});"
            rb = f"DROP TYPE IF EXISTS {enum_name};"
            statements.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op.get("type") == "drop_type":
            enum_name = op["enum_name"]
            up = f"DROP TYPE IF EXISTS {enum_name};"
            values_sql = ", ".join(repr(v) for v in op.get("values", []))
            rb = f"CREATE TYPE {enum_name} AS ENUM ({values_sql});"
            statements.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up, rollback_sql=rb,
            ))
    return statements


def _handler_diff_sql(
    handler: EnumHandler,
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[str, str, list[Change]]:
    """Use the handler to diff and emit, returning SQL."""
    snap_spec = handler.canonicalize(handler.extract(snapshot))
    model_spec = handler.canonicalize(
        handler.model_spec_from_tables(model_tables)
    )
    upgrade_ops, rollback_ops = handler.diff(snap_spec, model_spec)

    all_stmts: list[MigrationStatement] = []
    for op in upgrade_ops:
        all_stmts.extend(handler.emit(op))
    for op in rollback_ops:
        all_stmts.extend(handler.emit(op))

    up_sql, rb_sql = _assemble_migration(all_stmts)
    return up_sql, rb_sql, []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HANDLER = EnumHandler()

SNAPSHOT_NO_ENUMS: dict[str, Any] = {"enums": {}}
SNAPSHOT_MOOD: dict[str, Any] = {
    "enums": {"mood": ["happy", "sad"]},
}
SNAPSHOT_MOOD_SIZE: dict[str, Any] = {
    "enums": {
        "mood": ["happy", "sad"],
        "size": ["small", "medium", "large"],
    },
}

MODEL_MOOD_PLUS_ECSTATIC = _make_model_table([
    {
        "name": "mood_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad", "ecstatic"],
            }
        },
    },
])

MODEL_MOOD_SAME = _make_model_table([
    {
        "name": "mood_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad"],
            }
        },
    },
])

MODEL_MOOD_TWO_COLS = _make_model_table([
    {
        "name": "col_a",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad"],
            }
        },
    },
    {
        "name": "col_b",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad"],
            }
        },
    },
])

MODEL_NEW_SIZE = _make_model_table([
    {
        "name": "size_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "size",
                "values": ["small", "medium", "large"],
            }
        },
    },
])

MODEL_MOOD_PLUS_ECSTATIC_TWO_COLS = _make_model_table([
    {
        "name": "col_a",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad", "ecstatic"],
            }
        },
    },
    {
        "name": "col_b",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad", "ecstatic"],
            }
        },
    },
])

MODEL_MOOD_PLUS_MEH = _make_model_table([
    {
        "name": "mood_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "meh", "sad"],
            }
        },
    },
])

MODEL_MOOD_SIZE = _make_model_table([
    {
        "name": "mood_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "mood",
                "values": ["happy", "sad"],
            }
        },
    },
    {
        "name": "size_col",
        "pg_meta": {
            "pg_type": {
                "kind": "enum",
                "type_name": "size",
                "values": ["small", "medium", "large"],
            }
        },
    },
])


# ---------------------------------------------------------------------------
# Golden byte-equivalence tests
# ---------------------------------------------------------------------------

class TestEnumHandlerGolden:
    @pytest.mark.parametrize(
        "snapshot,model_tables,label",
        [
            (SNAPSHOT_MOOD, MODEL_MOOD_SAME, "unchanged"),
            (SNAPSHOT_MOOD, MODEL_MOOD_PLUS_ECSTATIC, "add_value"),
            (SNAPSHOT_MOOD, MODEL_MOOD_PLUS_MEH, "add_value_after"),
            (SNAPSHOT_MOOD, MODEL_MOOD_TWO_COLS, "two_cols_unchanged"),
            (
                SNAPSHOT_MOOD,
                MODEL_MOOD_PLUS_ECSTATIC_TWO_COLS,
                "two_cols_add_value",
            ),
            (SNAPSHOT_NO_ENUMS, MODEL_MOOD_SAME, "model_only"),
            (SNAPSHOT_NO_ENUMS, MODEL_NEW_SIZE, "fresh_create"),
            (SNAPSHOT_MOOD, MODEL_NEW_SIZE, "create_new_enum"),
            (SNAPSHOT_MOOD_SIZE, MODEL_MOOD_SAME, "subset_no_new"),
            (SNAPSHOT_MOOD_SIZE, MODEL_MOOD_SIZE, "cross_enum_unchanged"),
        ],
    )
    def test_sql_byte_equivalence(
        self,
        snapshot: dict[str, Any],
        model_tables: list[FakeTable],
        label: str,
    ) -> None:
        inline_up_ops, inline_rb_ops = _inline_enum_diff(snapshot, model_tables)
        inline_stmts = _inline_enum_emit(inline_up_ops) + _inline_enum_emit(inline_rb_ops)
        inline_up_sql, inline_rb_sql = _assemble_migration(inline_stmts)

        handler_up_sql, handler_rb_sql, _ = _handler_diff_sql(
            HANDLER, snapshot, model_tables
        )

        assert handler_up_sql == inline_up_sql, (
            f"Upgrade SQL mismatch for {label}\n"
            f"  inline:  {inline_up_sql!r}\n"
            f"  handler: {handler_up_sql!r}"
        )
        assert handler_rb_sql == inline_rb_sql, (
            f"Rollback SQL mismatch for {label}\n"
            f"  inline:  {inline_rb_sql!r}\n"
            f"  handler: {handler_rb_sql!r}"
        )


# ---------------------------------------------------------------------------
# Contract tests for EnumHandler
# ---------------------------------------------------------------------------

class TestEnumHandlerContract:
    def test_canonical_idempotent(self) -> None:
        spec = {"Mood": ["Happy", "Sad"], "Size": ["Small"]}
        c1 = HANDLER.canonicalize(spec)
        c2 = HANDLER.canonicalize(c1)
        assert c1 == c2
        assert "Mood" not in c1
        assert "mood" in c1

    def test_canonical_empty(self) -> None:
        assert HANDLER.canonicalize({}) == {}
        assert HANDLER.canonicalize(None) == {}

    def test_unchanged_produces_empty_diff(self) -> None:
        snap_spec = HANDLER.canonicalize(HANDLER.extract(SNAPSHOT_MOOD))
        model_spec = HANDLER.canonicalize(
            HANDLER.model_spec_from_tables(MODEL_MOOD_SAME)
        )
        up, rb = HANDLER.diff(snap_spec, model_spec)
        assert up == []
        assert rb == []

    def test_add_value_is_irreversible(self) -> None:
        snap_spec = HANDLER.canonicalize(HANDLER.extract(SNAPSHOT_MOOD))
        model_spec = HANDLER.canonicalize(
            HANDLER.model_spec_from_tables(MODEL_MOOD_PLUS_ECSTATIC)
        )
        up, _ = HANDLER.diff(snap_spec, model_spec)
        for op in up:
            if op.object_type == "alter_enum_add_value":
                assert op.irreversible

    def test_create_type_is_reversible(self) -> None:
        snap_spec = HANDLER.canonicalize(HANDLER.extract(SNAPSHOT_NO_ENUMS))
        model_spec = HANDLER.canonicalize(
            HANDLER.model_spec_from_tables(MODEL_NEW_SIZE)
        )
        up, _ = HANDLER.diff(snap_spec, model_spec)
        for op in up:
            if op.object_type == "create_type":
                assert not op.irreversible

    def test_two_cols_dedupe(self) -> None:
        spec = HANDLER.model_spec_from_tables(MODEL_MOOD_TWO_COLS)
        assert len(spec) == 1
        assert spec.get("mood") or spec.get("Mood")
        key = next(k for k in spec if k.lower() == "mood")
        assert spec[key] == ["happy", "sad"]

    def test_conflicting_values_raises(self) -> None:
        bad_model = _make_model_table([
            {
                "name": "a",
                "pg_meta": {
                    "pg_type": {
                        "kind": "enum",
                        "type_name": "mood",
                        "values": ["happy", "sad"],
                    }
                },
            },
            {
                "name": "b",
                "pg_meta": {
                    "pg_type": {
                        "kind": "enum",
                        "type_name": "mood",
                        "values": ["happy", "angry"],
                    }
                },
            },
        ])
        with pytest.raises(ValueError, match="conflicting"):
            HANDLER.model_spec_from_tables(bad_model)

    def test_forward_then_rollback_revert_comment(self) -> None:
        """Emit produces -- Revert: for add-value ops."""
        snap_spec = HANDLER.canonicalize(HANDLER.extract(SNAPSHOT_MOOD))
        model_spec = HANDLER.canonicalize(
            HANDLER.model_spec_from_tables(MODEL_MOOD_PLUS_ECSTATIC)
        )
        up, rb = HANDLER.diff(snap_spec, model_spec)
        for op in up:
            stmts = HANDLER.emit(op)
            for stmt in stmts:
                assert "-- Revert:" in stmt.rollback_sql
        for op in rb:
            stmts = HANDLER.emit(op)
            for stmt in stmts:
                assert "-- Revert:" in stmt.upgrade_sql


# ---------------------------------------------------------------------------
# Orchestration tests
# ---------------------------------------------------------------------------

class TestRegistryDriver:
    def test_zero_handlers_returns_empty(self) -> None:
        from dbwarden.engine.pg_registry import RegistryDriver
        driver = RegistryDriver()
        up, rb = driver.run({}, [], None)
        assert up == []
        assert rb == []

    def test_driver_with_enum_handler_add_value(self) -> None:
        from dbwarden.engine.pg_registry import RegistryDriver
        driver = RegistryDriver()
        driver.register(HANDLER)
        up, rb = driver.run(SNAPSHOT_MOOD, MODEL_MOOD_PLUS_ECSTATIC, None)
        assert len(up) == 1
        assert up[0].object_type == "alter_enum_add_value"
        assert up[0].irreversible

    def test_driver_with_enum_handler_create_type(self) -> None:
        from dbwarden.engine.pg_registry import RegistryDriver
        driver = RegistryDriver()
        driver.register(HANDLER)
        up, rb = driver.run(SNAPSHOT_NO_ENUMS, MODEL_NEW_SIZE, None)
        create_types = [op for op in up if op.object_type == "create_type"]
        assert len(create_types) == 1

    def test_driver_emit_all(self) -> None:
        from dbwarden.engine.pg_registry import RegistryDriver
        driver = RegistryDriver()
        driver.register(HANDLER)
        up, rb = driver.run(SNAPSHOT_MOOD, MODEL_MOOD_PLUS_ECSTATIC, None)
        up_sql, rb_sql, _ = driver.emit_op_to_sql(up, rb)
        assert "ALTER TYPE mood ADD VALUE IF NOT EXISTS 'ecstatic'" in up_sql
        assert "-- Revert:" in rb_sql
