from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class EnumHandler(ObjectHandler):
    """Handler for PostgreSQL ENUM types.

    Phase 0 reference implementation that ports the inline enum logic from
    ``diff_models_against_snapshot`` (lines 3387--3426) and
    ``snapshot_diff_to_sql`` (lines 4403--4441) into the registry interface.
    """

    object_type: str = "enum"
    op_types: tuple[str, ...] = (
        "alter_enum_add_value",
        "create_type",
        "drop_type",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.CREATE_TYPE

    # ------------------------------------------------------------------
    # Extract -- wraps ``inspector.get_enums()`` logic
    # ------------------------------------------------------------------

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("enums", {}))

    # ------------------------------------------------------------------
    # Model spec (PREAMBLE path) -- enums are never in config
    # ------------------------------------------------------------------

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Model spec (DIFF path) -- collect enums from model table columns
    # ------------------------------------------------------------------

    def model_spec_from_tables(
        self, model_tables: list[Any]
    ) -> dict[str, Any]:
        spec: dict[str, list[str]] = {}
        for table in model_tables:
            for col in table.columns:
                pg_type = col.pg_meta.get("pg_type", {})
                if pg_type.get("kind") == "enum":
                    type_name: str | None = pg_type.get("type_name")
                    values: list[str] = pg_type.get("values", [])
                    if type_name:
                        if type_name in spec:
                            existing = spec[type_name]
                            if existing != values:
                                msg = (
                                    f"Enum {type_name!r} has conflicting "
                                    f"value lists: {existing} vs {values}"
                                )
                                raise ValueError(msg)
                        else:
                            spec[type_name] = values
        return spec

    # ------------------------------------------------------------------
    # Canonicalize -- total over dicts, keys lowercased for stable match
    # ------------------------------------------------------------------

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, list[str]] = {}
        for k, v in spec.items():
            key = k.lower()
            result[key] = list(v)
        return result

    # ------------------------------------------------------------------
    # Diff -- produce add-value and create-type ops
    # ------------------------------------------------------------------

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        snap = snap_spec or {}
        model = model_spec or {}

        for enum_name, snap_values in snap.items():
            model_values = model.get(enum_name)
            if model_values is None:
                continue
            snap_set = set(snap_values)
            new_values = [v for v in model_values if v not in snap_set]
            if new_values:
                pos_map = {v: i for i, v in enumerate(model_values)}
                for v in new_values:
                    idx = pos_map[v]
                    after: str | None = model_values[idx - 1] if idx > 0 else None
                    upgrade_attrs: dict[str, Any] = {
                        "enum_name": enum_name,
                        "value": v,
                        "after": after,
                    }
                    rollback_attrs: dict[str, Any] = {
                        "enum_name": enum_name,
                        "value": v,
                        "revert": True,
                        "after": after,
                    }
                    upgrade_ops.append(
                        Op(
                            object_type="alter_enum_add_value",
                            upgrade_attrs=upgrade_attrs,
                            rollback_attrs=rollback_attrs,
                            irreversible=True,
                        )
                    )
                    rollback_ops.append(
                        Op(
                            object_type="alter_enum_add_value",
                            upgrade_attrs=rollback_attrs,
                            rollback_attrs=upgrade_attrs,
                            irreversible=True,
                        )
                    )

        for enum_name, curr_values in model.items():
            if enum_name not in snap:
                upgrade_ops.append(
                    Op(
                        object_type="create_type",
                        upgrade_attrs={"enum_name": enum_name, "values": curr_values},
                        rollback_attrs={"enum_name": enum_name},
                    )
                )
                rollback_ops.append(
                    Op(
                        object_type="drop_type",
                        upgrade_attrs={
                            "enum_name": enum_name,
                            "values": curr_values,
                        },
                        rollback_attrs={
                            "enum_name": enum_name,
                            "values": curr_values,
                        },
                    )
                )

        return upgrade_ops, rollback_ops

    # ------------------------------------------------------------------
    # Emit -- produce MigrationStatement(s) for a single Op
    # ------------------------------------------------------------------

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []

        if op.object_type == "alter_enum_add_value":
            enum_name = op.upgrade_attrs["enum_name"]
            value = op.upgrade_attrs["value"]
            after = op.upgrade_attrs.get("after")
            after_clause = f" AFTER {after!r}" if after else ""
            revert = op.upgrade_attrs.get("revert", False)

            if revert:
                up = f"-- Revert: {value} was added to enum {enum_name}"
                rb = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
            else:
                up = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
                rb = f"-- Revert: {value} was added to enum {enum_name}"

            stmts.append(
                MigrationStatement(
                    order=StatementOrder.ALTER_TABLE_OPTIONS,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        elif op.object_type == "create_type":
            enum_name = op.upgrade_attrs["enum_name"]
            values = op.upgrade_attrs.get("values", [])
            values_sql = ", ".join(repr(v) for v in values)
            up = f"CREATE TYPE {enum_name} AS ENUM ({values_sql});"
            rb = f"DROP TYPE IF EXISTS {enum_name};"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_TYPE,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        elif op.object_type == "drop_type":
            enum_name = op.upgrade_attrs["enum_name"]
            up = f"DROP TYPE IF EXISTS {enum_name};"
            values = op.upgrade_attrs.get("values") or op.rollback_attrs.get("values", [])
            values_sql = ", ".join(repr(v) for v in values)
            rb = f"CREATE TYPE {enum_name} AS ENUM ({values_sql});"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_TYPE,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        return stmts
