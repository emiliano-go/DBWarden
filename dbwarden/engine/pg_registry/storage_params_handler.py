from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class StorageParamsHandler(ObjectHandler):
    object_type: str = "pg_storage_param"
    op_types: tuple[str, ...] = (
        "alter_pg_storage_param",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_OPTIONS

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            pg_table = tdata.get("pg_table") or tdata.get("backend_table_spec") or {}
            params = pg_table.get("pg_storage_params", {}) or {}
            if params:
                result[tname] = dict(params)
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            pg_table = table.pg_table or {}
            params = pg_table.get("pg_storage_params", {}) or {}
            if params:
                result[table.name] = dict(params)
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        return spec

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        all_tables = set(snap_spec.keys()) | set(model_spec.keys())
        for tname in sorted(all_tables):
            snap_params = snap_spec.get(tname, {})
            model_params = model_spec.get(tname, {})
            all_keys = set(snap_params.keys()) | set(model_params.keys())
            for key in sorted(all_keys):
                snap_val = snap_params.get(key)
                model_val = model_params.get(key)
                if snap_val != model_val:
                    upgrade_ops.append(Op(
                        object_type="alter_pg_storage_param",
                        upgrade_attrs={
                            "table": tname,
                            "param": key,
                            "to_value": model_val,
                            "from_value": snap_val,
                        },
                        rollback_attrs={
                            "table": tname,
                            "param": key,
                            "to_value": snap_val,
                            "from_value": model_val,
                        },
                    ))
                    rollback_ops.append(Op(
                        object_type="alter_pg_storage_param",
                        upgrade_attrs={
                            "table": tname,
                            "param": key,
                            "to_value": snap_val,
                            "from_value": model_val,
                        },
                        rollback_attrs={
                            "table": tname,
                            "param": key,
                            "to_value": model_val,
                            "from_value": snap_val,
                        },
                    ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        table = op.upgrade_attrs["table"]
        param = op.upgrade_attrs["param"]
        to_val = op.upgrade_attrs.get("to_value")
        from_val = op.upgrade_attrs.get("from_value")

        if to_val is not None:
            up = f"ALTER TABLE {table} SET ({param} = {to_val});"
        else:
            up = f"ALTER TABLE {table} RESET ({param});"
        if from_val is not None:
            rb = f"ALTER TABLE {table} SET ({param} = {from_val});"
        else:
            rb = f"ALTER TABLE {table} RESET ({param});"

        stmts.append(MigrationStatement(
            order=StatementOrder.ALTER_TABLE_OPTIONS,
            upgrade_sql=up, rollback_sql=rb,
        ))
        return stmts
