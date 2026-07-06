from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class FunctionHandler(ObjectHandler):
    object_type: str = "function"
    op_types: tuple[str, ...] = (
        "create_function",
        "drop_function",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("functions", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_functions", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {}
            if entry.get("definition"):
                info["definition"] = entry["definition"]
            if entry.get("schema"):
                info["schema"] = entry["schema"]
            spec[name] = info
        return spec

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for key, val in spec.items():
            if val is None:
                continue
            entry: dict[str, Any] = {}
            if isinstance(val, dict):
                if val.get("definition"):
                    entry["definition"] = val["definition"].strip()
                if val.get("schema"):
                    entry["schema"] = str(val["schema"])
            result[key] = entry
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

        for name, info in model.items():
            if name not in snap:
                upgrade_ops.append(Op(
                    object_type="create_function",
                    upgrade_attrs={"function_name": name, "function_info": info},
                    rollback_attrs={"function_name": name, "function_info": info},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_function",
                    upgrade_attrs={"function_name": name, "function_info": info},
                    rollback_attrs={"function_name": name, "function_info": info},
                ))
            else:
                snap_info = snap[name]
                if snap_info.get("definition") != info.get("definition") or snap_info.get("schema") != info.get("schema"):
                    upgrade_ops.append(Op(
                        object_type="create_function",
                        upgrade_attrs={"function_name": name, "function_info": info},
                        rollback_attrs={"function_name": name, "function_info": snap_info},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_function",
                        upgrade_attrs={"function_name": name, "function_info": snap_info},
                        rollback_attrs={"function_name": name, "function_info": snap_info},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_function",
                    upgrade_attrs={"function_name": name, "function_info": snap_info},
                    rollback_attrs={"function_name": name, "function_info": snap_info},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_function",
                    upgrade_attrs={"function_name": name, "function_info": snap_info},
                    rollback_attrs={"function_name": name, "function_info": snap_info},
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_function":
            info = op.upgrade_attrs.get("function_info", {})
            name = op.upgrade_attrs["function_name"]
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            definition = info.get("definition", "") if isinstance(info, dict) else ""
            if definition:
                up = f"CREATE OR REPLACE FUNCTION {qname}\n{definition};"
            else:
                up = f"-- Function {qname} definition missing; cannot generate DDL"
            rb = f"DROP FUNCTION IF EXISTS {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_EXTENSION,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "drop_function":
            name = op.upgrade_attrs["function_name"]
            schema = None
            info = op.upgrade_attrs.get("function_info")
            if isinstance(info, dict):
                schema = info.get("schema")
            qname = _qualified_name(name, schema)
            up = f"DROP FUNCTION IF EXISTS {qname};"
            if isinstance(info, dict) and info.get("definition"):
                rb = f"CREATE OR REPLACE FUNCTION {qname}\n{info['definition']};"
            else:
                rb = f"-- Revert: CREATE OR REPLACE FUNCTION {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_EXTENSION,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
