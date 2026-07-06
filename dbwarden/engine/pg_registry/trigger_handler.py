from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class TriggerHandler(ObjectHandler):
    object_type: str = "trigger"
    op_types: tuple[str, ...] = (
        "create_trigger",
        "drop_trigger",
        "alter_trigger",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_OPTIONS

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            trigs = tdata.get("pg_triggers", [])
            if trigs:
                result[tname] = {t["name"]: t for t in trigs}
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_triggers", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            table: str = entry.get("table", "")
            name: str = entry["name"]
            if table not in spec:
                spec[table] = {}
            info: dict[str, Any] = {"name": name}
            if entry.get("definition"):
                info["definition"] = entry["definition"]
            if entry.get("event"):
                info["event"] = entry["event"]
            spec[table][name] = info
        return spec

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for tname, triggers in spec.items():
            tresult: dict[str, Any] = {}
            for tname2, tinfo in triggers.items() if isinstance(triggers, dict) else []:
                pass
            for trig_name, trig_info in triggers.items():
                entry: dict[str, Any] = {"name": trig_name}
                if isinstance(trig_info, dict):
                    if trig_info.get("definition"):
                        entry["definition"] = trig_info["definition"].strip()
                    if trig_info.get("event"):
                        entry["event"] = trig_info["event"]
                tresult[trig_name] = entry
            if tresult:
                result[tname] = tresult
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
            snap_trigs = snap.get(tname, {})
            model_trigs = model.get(tname, {})
            all_names = set(snap_trigs.keys()) | set(model_trigs.keys())
            for name in sorted(all_names):
                snap_t = snap_trigs.get(name)
                model_t = model_trigs.get(name)
                if snap_t and not model_t:
                    upgrade_ops.append(Op(
                        object_type="drop_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(snap_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(snap_t or {})},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="create_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(snap_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(snap_t or {})},
                    ))
                elif model_t and not snap_t:
                    upgrade_ops.append(Op(
                        object_type="create_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(model_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(model_t or {})},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(model_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(model_t or {})},
                    ))
                elif model_t != snap_t:
                    upgrade_ops.append(Op(
                        object_type="drop_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(snap_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(model_t or {})},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="create_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(snap_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(model_t or {})},
                    ))
                    upgrade_ops.append(Op(
                        object_type="create_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(model_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(snap_t or {})},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_trigger",
                        upgrade_attrs={"table": tname, "name": name, **(model_t or {})},
                        rollback_attrs={"table": tname, "name": name, **(snap_t or {})},
                    ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []
        table = op.upgrade_attrs["table"]
        name = op.upgrade_attrs["name"]
        qtable = _qualified_name(table, op.upgrade_attrs.get("schema"))
        definition = op.upgrade_attrs.get("definition", "")

        if op.object_type == "create_trigger":
            if definition:
                up = definition
            else:
                up = f"-- Trigger {name} definition missing; cannot generate DDL"
            rb = f"DROP TRIGGER IF EXISTS {name} ON {qtable};"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=up,
                rollback_sql=rb,
            ))
        elif op.object_type == "drop_trigger":
            up = f"DROP TRIGGER IF EXISTS {name} ON {qtable};"
            if definition:
                rb = definition
            else:
                rb = f"-- Revert: CREATE TRIGGER {name} ON {qtable};"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=up,
                rollback_sql=rb,
            ))
        elif op.object_type == "alter_trigger":
            up = f"-- ALTER TRIGGER {name} ON {qtable}; -- not yet implemented"
            rb = f"-- Revert ALTER TRIGGER {name} ON {qtable};"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
