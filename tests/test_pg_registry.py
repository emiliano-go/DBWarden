"""Golden tests and contract tests for Phase 0 pg_registry module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from dbwarden.engine.migration_name import Change
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
    """Inline extraction : exact copy of snapshot.py:3395-3396."""
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
    """Inline diff : exact copy of snapshot.py:3393-3426."""
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
    """Inline emit : exact copy of snapshot.py:4403-4441."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
# Orchestration tests
# ---------------------------------------------------------------------------

class TestRegistryDriver:
    def test_zero_handlers_returns_empty(self) -> None:
        from dbwarden.engine.core.registry import RegistryDriver
        driver = RegistryDriver()
        up, rb = driver.run({}, [], None)
        assert up == []
        assert rb == []
