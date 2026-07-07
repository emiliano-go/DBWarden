from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class StatisticsHandler(ObjectHandler):
    object_type: str = "statistics"
    op_types: tuple[str, ...] = (
        "alter_column_statistics",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_OPTIONS

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            cols = tdata.get("columns", {})
            for cname, cinfo in cols.items():
                pg_col = cinfo.get("pg_column", {})
                if isinstance(pg_col, dict) and pg_col.get("statistics") is not None:
                    if tname not in result:
                        result[tname] = {}
                    result[tname][cname] = pg_col["statistics"]
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            pg_table = table.pg_table or {}
            for col in table.columns:
                pg_col = col.pg_meta.get("pg_column", {})
                if isinstance(pg_col, dict) and pg_col.get("statistics") is not None:
                    if table.name not in result:
                        result[table.name] = {}
                    result[table.name][col.name] = pg_col["statistics"]
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, int]] = {}
        for tname, cols in spec.items():
            if isinstance(cols, dict):
                for cname, val in cols.items():
                    if tname not in result:
                        result[tname] = {}
                    try:
                        result[tname][cname] = int(val)
                    except (ValueError, TypeError):
                        pass
        return result

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        snap = snap_spec or {}
        model = model_spec or {}

        all_tables = set(snap.keys()) | set(model.keys())
        for tname in sorted(all_tables):
            snap_cols = snap.get(tname, {})
            model_cols = model.get(tname, {})
            all_cols = set(snap_cols.keys()) | set(model_cols.keys())
            for cname in sorted(all_cols):
                snap_val = snap_cols.get(cname)
                model_val = model_cols.get(cname)
                if snap_val != model_val:
                    upgrade_attrs: dict[str, Any] = {
                        "table": tname,
                        "column": cname,
                        "statistics": model_val,
                    }
                    rollback_attrs: dict[str, Any] = {
                        "table": tname,
                        "column": cname,
                        "statistics": snap_val,
                    }
                    upgrade_ops.append(Op(
                        object_type="alter_column_statistics",
                        upgrade_attrs=upgrade_attrs,
                        rollback_attrs=rollback_attrs,
                    ))
                    rollback_ops.append(Op(
                        object_type="alter_column_statistics",
                        upgrade_attrs=rollback_attrs,
                        rollback_attrs=upgrade_attrs,
                    ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []
        table = op.upgrade_attrs["table"]
        column = op.upgrade_attrs["column"]
        statistics = op.upgrade_attrs.get("statistics")
        qtable = _qualified_name(table, op.upgrade_attrs.get("schema"))

        if statistics is not None:
            up = f"ALTER TABLE {qtable} ALTER COLUMN {column} SET STATISTICS {statistics};"
            rb = f"-- Revert ALTER TABLE {qtable} ALTER COLUMN {column} SET STATISTICS;"
        else:
            up = f"ALTER TABLE {qtable} ALTER COLUMN {column} SET STATISTICS -1;"
            rb = f"-- Revert ALTER TABLE {qtable} ALTER COLUMN {column} SET STATISTICS;"

        stmts.append(MigrationStatement(
            order=StatementOrder.ALTER_TABLE_OPTIONS,
            upgrade_sql=up,
            rollback_sql=rb,
        ))

        return stmts
