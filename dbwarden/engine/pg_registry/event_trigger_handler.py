from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class EventTriggerHandler(ObjectHandler):
    object_type: str = "event_trigger"
    op_types: tuple[str, ...] = (
        "create_event_trigger",
        "drop_event_trigger",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_TYPE

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("event_triggers", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_event_triggers", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {
                "event": entry["event"],
                "function": dict(entry.get("function", {})),
            }
            if entry.get("tags"):
                info["tags"] = list(entry["tags"])
            if entry.get("enabled"):
                info["enabled"] = str(entry["enabled"])
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
                entry: dict[str, Any] = {
                    "event": str(val.get("event", "")),
                    "function": dict(val.get("function", {})),
                }
                if val.get("tags"):
                    entry["tags"] = sorted(val["tags"])
                if val.get("enabled"):
                    entry["enabled"] = str(val["enabled"])
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
                    object_type="create_event_trigger",
                    upgrade_attrs={"trigger_name": name, "trigger_info": info},
                    rollback_attrs={"trigger_name": name, "trigger_info": info},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_event_trigger",
                    upgrade_attrs={"trigger_name": name, "trigger_info": info},
                    rollback_attrs={"trigger_name": name, "trigger_info": info},
                ))
            else:
                snap_info = snap[name]
                if snap_info != info:
                    upgrade_ops.append(Op(
                        object_type="create_event_trigger",
                        upgrade_attrs={"trigger_name": name, "trigger_info": info},
                        rollback_attrs={"trigger_name": name, "trigger_info": snap_info},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_event_trigger",
                        upgrade_attrs={"trigger_name": name, "trigger_info": snap_info},
                        rollback_attrs={"trigger_name": name, "trigger_info": info},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_event_trigger",
                    upgrade_attrs={"trigger_name": name, "trigger_info": snap_info},
                    rollback_attrs={"trigger_name": name, "trigger_info": snap_info},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_event_trigger",
                    upgrade_attrs={"trigger_name": name, "trigger_info": snap_info},
                    rollback_attrs={"trigger_name": name, "trigger_info": snap_info},
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name, _quote_pg

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_event_trigger":
            info = op.upgrade_attrs.get("trigger_info", {})
            name = op.upgrade_attrs["trigger_name"]
            event = info.get("event", "") if isinstance(info, dict) else ""
            fn_info = info.get("function", {}) if isinstance(info, dict) else {}
            fn_schema = fn_info.get("schema") if isinstance(fn_info, dict) else None
            fn_name = fn_info.get("name") if isinstance(fn_info, dict) else ""
            fn_qname = _qualified_name(fn_name, fn_schema)
            tags = info.get("tags") if isinstance(info, dict) else None

            when_clause = ""
            if tags:
                quoted_tags = ", ".join(f"'{t}'" for t in tags)
                when_clause = f" WHEN tag IN ({quoted_tags})"

            up = f"CREATE EVENT TRIGGER {_quote_pg(name)} ON {event}{when_clause} EXECUTE FUNCTION {fn_qname}();"
            rb = f"DROP EVENT TRIGGER IF EXISTS {_quote_pg(name)};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "drop_event_trigger":
            name = op.upgrade_attrs["trigger_name"]
            qname = _quote_pg(name)
            up = f"DROP EVENT TRIGGER IF EXISTS {qname};"

            info = op.upgrade_attrs.get("trigger_info")
            if isinstance(info, dict):
                event = info.get("event", "")
                fn_info = info.get("function", {})
                fn_schema = fn_info.get("schema") if isinstance(fn_info, dict) else None
                fn_name = fn_info.get("name") if isinstance(fn_info, dict) else ""
                fn_qname = _qualified_name(fn_name, fn_schema)
                tags = info.get("tags")
                when_clause = ""
                if tags:
                    quoted_tags = ", ".join(f"'{t}'" for t in tags)
                    when_clause = f" WHEN tag IN ({quoted_tags})"
                rb = f"CREATE EVENT TRIGGER {qname} ON {event}{when_clause} EXECUTE FUNCTION {fn_qname}();"
            else:
                rb = f"-- Revert: CREATE EVENT TRIGGER {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
