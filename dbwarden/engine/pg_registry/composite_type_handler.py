from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class CompositeTypeHandler(ObjectHandler):
    object_type: str = "composite_type"
    op_types: tuple[str, ...] = (
        "create_composite_type",
        "drop_composite_type",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_TYPE

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("composite_types", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_composite_types", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {
                "columns": list(entry.get("columns", [])),
            }
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
            if isinstance(val, dict):
            #    entry: dict[str, Any] = {"columns": sorted(val.get("columns", []), key=lambda c: c.get("name", ""))}
                entry: dict[str, Any] = {"columns": list(val.get("columns", []))}
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
                    object_type="create_composite_type",
                    upgrade_attrs={"type_name": name, "type_info": info},
                    rollback_attrs={"type_name": name, "type_info": info},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_composite_type",
                    upgrade_attrs={"type_name": name, "type_info": info},
                    rollback_attrs={"type_name": name, "type_info": info},
                ))
            else:
                snap_info = snap[name]
                if snap_info != info:
                    upgrade_ops.append(Op(
                        object_type="create_composite_type",
                        upgrade_attrs={"type_name": name, "type_info": info},
                        rollback_attrs={"type_name": name, "type_info": snap_info},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_composite_type",
                        upgrade_attrs={"type_name": name, "type_info": snap_info},
                        rollback_attrs={"type_name": name, "type_info": info},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_composite_type",
                    upgrade_attrs={"type_name": name, "type_info": snap_info},
                    rollback_attrs={"type_name": name, "type_info": snap_info},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_composite_type",
                    upgrade_attrs={"type_name": name, "type_info": snap_info},
                    rollback_attrs={"type_name": name, "type_info": snap_info},
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name, _quote_pg

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_composite_type":
            info = op.upgrade_attrs.get("type_info", {})
            name = op.upgrade_attrs["type_name"]
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            columns = info.get("columns", []) if isinstance(info, dict) else []
            col_defs = ", ".join(
                f"{_quote_pg(c.get('name', ''))} {c.get('type', 'text')}"
                for c in columns
            )
            up = f"CREATE TYPE {qname} AS ({col_defs});"
            rb = f"DROP TYPE IF EXISTS {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "drop_composite_type":
            name = op.upgrade_attrs["type_name"]
            schema = None
            info = op.upgrade_attrs.get("type_info")
            if isinstance(info, dict):
                schema = info.get("schema")
            qname = _qualified_name(name, schema)
            up = f"DROP TYPE IF EXISTS {qname};"
            if isinstance(info, dict):
                columns = info.get("columns", [])
                col_defs = ", ".join(
                    f"{_quote_pg(c.get('name', ''))} {c.get('type', 'text')}"
                    for c in columns
                )
                rb = f"CREATE TYPE {qname} AS ({col_defs});"
            else:
                rb = f"-- Revert: CREATE TYPE {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
