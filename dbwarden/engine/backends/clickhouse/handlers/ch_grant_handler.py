from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChGrantHandler(ObjectHandler):
    object_type: str = "ch_grant"
    op_types: tuple[str, ...] = (
        "grant_ch_privilege",
        "revoke_ch_privilege",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, info in snapshot.get("grants", {}).items():
            result[key] = {
                "privileges": list(info.get("privileges", [])),
                "on": info.get("on", ""),
                "to": info.get("to", ""),
                "with_grant_option": info.get("with_grant_option", False),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for entry in getattr(config, "ch_grants", []) or []:
            d = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
            key = f"{d['to']}:{d['on']}"
            result[key] = d
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        return {k: dict(v) for k, v in spec.items() if v is not None} if spec else {}

    def diff(self, snap_spec: dict[str, Any], model_spec: dict[str, Any]) -> Tuple[List[Op], List[Op]]:
        up, rb = [], []
        snap, model = snap_spec or {}, model_spec or {}
        for key, info in model.items():
            if key not in snap:
                up.append(Op("grant_ch_privilege", {"key": key, **info}, {}))
                rb.insert(0, Op("revoke_ch_privilege", {"key": key, **info}, {}))
            else:
                si = snap[key]
                if si.get("privileges") != info.get("privileges") or si.get("with_grant_option") != info.get("with_grant_option"):
                    up.append(Op("grant_ch_privilege", {"key": key, **info}, {"key": key, **si}))
                    rb.insert(0, Op("grant_ch_privilege", {"key": key, **si}, {"key": key, **info}))
        for key in snap:
            if key not in model:
                si = snap[key]
                rb.insert(0, Op("grant_ch_privilege", {"key": key, **si}, {}))
                up.append(Op("revoke_ch_privilege", {"key": key, **si}, {}))
        return up, rb

    def emit(self, op: Op, db_name: Optional[str] = None, **kwargs: Any) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        privs = op.upgrade_attrs.get("privileges", [])
        on = op.upgrade_attrs.get("on", "")
        to = op.upgrade_attrs.get("to", "")
        wgo = op.upgrade_attrs.get("with_grant_option", False)
        grant_opt = " WITH GRANT OPTION" if wgo else ""
        priv_list = ", ".join(privs)

        if op.object_type == "grant_ch_privilege":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"GRANT {priv_list} ON {on} TO {to}{grant_opt};",
                rollback_sql=f"REVOKE {priv_list} ON {on} FROM {to};",
            ))
        elif op.object_type == "revoke_ch_privilege":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"REVOKE {priv_list} ON {on} FROM {to};",
                rollback_sql=f"GRANT {priv_list} ON {on} TO {to}{grant_opt};",
            ))
        return stmts
