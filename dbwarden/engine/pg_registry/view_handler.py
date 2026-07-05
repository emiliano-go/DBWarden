from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
    _normalize_view_def,
)


class ViewHandler(ObjectHandler):
    object_type: str = "view"
    op_types: tuple[str, ...] = (
        "alter_view",
        "refresh_matview",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_VIEW

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            obj_type = tdata.get("object_type", "table")
            if obj_type not in ("view", "materialized_view"):
                continue
            result[tname] = {
                "pg_view_definition": tdata.get("pg_view_definition"),
                "pg_view_materialized": tdata.get("pg_view_materialized", False),
                "pg_view_auto_refresh": tdata.get("pg_view_auto_refresh", False),
                "object_type": obj_type,
                "schema": tdata.get("schema"),
            }
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            obj_type = getattr(table, "object_type", "table")
            if obj_type not in ("view", "materialized_view"):
                continue
            result[table.name] = {
                "pg_view_definition": table.pg_view_definition,
                "pg_view_materialized": table.pg_view_materialized,
                "pg_view_auto_refresh": table.pg_view_auto_refresh or False,
                "object_type": obj_type,
                "schema": table.schema,
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for tname, entry in spec.items():
            result[tname] = {
                "pg_view_definition": _normalize_view_def(entry.get("pg_view_definition")),
                "pg_view_materialized": bool(entry.get("pg_view_materialized", False)),
                "pg_view_auto_refresh": bool(entry.get("pg_view_auto_refresh", False)),
                "object_type": entry.get("object_type", "view"),
                "schema": entry.get("schema"),
            }
        return result

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        all_tables = set(snap_spec.keys()) | set(model_spec.keys())
        for tname in sorted(all_tables):
            snap_entry = snap_spec.get(tname) or {}
            model_entry = model_spec.get(tname) or {}

            snap_def = snap_entry.get("pg_view_definition")
            model_def = model_entry.get("pg_view_definition")
            snap_mat = snap_entry.get("pg_view_materialized", False)
            model_mat = model_entry.get("pg_view_materialized", False)

            if snap_def != model_def or snap_mat != model_mat:
                upgrade_ops.append(Op(
                    object_type="alter_view",
                    upgrade_attrs={
                        "table": tname,
                        "pg_view_definition": model_entry.get("pg_view_definition"),
                        "pg_view_materialized": model_mat,
                        "snap_pg_view_definition": snap_entry.get("pg_view_definition"),
                        "snap_pg_view_materialized": snap_mat,
                        "schema": model_entry.get("schema"),
                    },
                    rollback_attrs={
                        "table": tname,
                        "pg_view_definition": snap_entry.get("pg_view_definition"),
                        "pg_view_materialized": snap_mat,
                        "snap_pg_view_definition": model_entry.get("pg_view_definition"),
                        "snap_pg_view_materialized": model_mat,
                        "schema": model_entry.get("schema"),
                    },
                ))
                rollback_ops.append(Op(
                    object_type="alter_view",
                    upgrade_attrs={
                        "table": tname,
                        "pg_view_definition": snap_entry.get("pg_view_definition"),
                        "pg_view_materialized": snap_mat,
                        "snap_pg_view_definition": model_entry.get("pg_view_definition"),
                        "snap_pg_view_materialized": model_mat,
                        "schema": model_entry.get("schema"),
                    },
                    rollback_attrs={
                        "table": tname,
                        "pg_view_definition": model_entry.get("pg_view_definition"),
                        "pg_view_materialized": model_mat,
                        "snap_pg_view_definition": snap_entry.get("pg_view_definition"),
                        "snap_pg_view_materialized": snap_mat,
                        "schema": model_entry.get("schema"),
                    },
                ))

            model_auto = model_entry.get("pg_view_auto_refresh", False)
            if model_entry.get("object_type") == "materialized_view" and model_auto:
                upgrade_ops.append(Op(
                    object_type="refresh_matview",
                    upgrade_attrs={
                        "table": tname,
                        "schema": model_entry.get("schema"),
                        "pg_view_auto_refresh": model_auto,
                    },
                    rollback_attrs={
                        "table": tname,
                        "schema": model_entry.get("schema"),
                        "pg_view_auto_refresh": model_auto,
                    },
                ))
                rollback_ops.append(Op(
                    object_type="refresh_matview",
                    upgrade_attrs={
                        "table": tname,
                        "schema": model_entry.get("schema"),
                        "pg_view_auto_refresh": model_auto,
                    },
                    rollback_attrs={
                        "table": tname,
                        "schema": model_entry.get("schema"),
                        "pg_view_auto_refresh": model_auto,
                    },
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []
        qname = _qualified_name(
            op.upgrade_attrs["table"],
            op.upgrade_attrs.get("schema"),
        )

        if op.object_type == "alter_view":
            view_def = op.upgrade_attrs.get("pg_view_definition") or ""
            mat = op.upgrade_attrs.get("pg_view_materialized", False)
            snap_mat = op.upgrade_attrs.get("snap_pg_view_materialized", False)
            rollback_def = op.upgrade_attrs.get("snap_pg_view_definition") or ""

            if mat and snap_mat:
                upgrade_sql = f"DROP MATERIALIZED VIEW IF EXISTS {qname};\nCREATE MATERIALIZED VIEW {qname} AS {view_def}"
            elif mat and not snap_mat:
                upgrade_sql = f"DROP VIEW IF EXISTS {qname};\nCREATE MATERIALIZED VIEW {qname} AS {view_def}"
            elif not mat and snap_mat:
                upgrade_sql = f"DROP MATERIALIZED VIEW IF EXISTS {qname};\nCREATE VIEW {qname} AS {view_def}"
            else:
                upgrade_sql = f"DROP VIEW IF EXISTS {qname};\nCREATE VIEW {qname} AS {view_def}"

            if snap_mat:
                rollback_sql = f"DROP MATERIALIZED VIEW IF EXISTS {qname};\nCREATE MATERIALIZED VIEW {qname} AS {rollback_def}"
            else:
                rollback_sql = f"DROP VIEW IF EXISTS {qname};\nCREATE VIEW {qname} AS {rollback_def}"

            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_VIEW,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
            ))

        elif op.object_type == "refresh_matview":
            upgrade_sql = f"REFRESH MATERIALIZED VIEW {qname};"
            rollback_sql = f"-- REFRESH MATERIALIZED VIEW {qname} (no rollback)"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_VIEW,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
            ))

        return stmts
