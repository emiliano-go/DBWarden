from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChRowPolicyHandler(ObjectHandler):
    object_type: str = "ch_row_policy"
    op_types: tuple[str, ...] = (
        "create_ch_row_policy",
        "drop_ch_row_policy",
        "alter_ch_row_policy",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, info in snapshot.get("row_policies", {}).items():
            result[name] = {
                "name": name,
                "table": info.get("table", ""),
                "using": info.get("using", ""),
                "to_roles": list(info.get("to_roles", [])),
                "permissive": info.get("permissive", True),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for entry in getattr(config, "ch_row_policies", []) or []:
            d = entry.to_dict() if hasattr(entry, "to_dict") else dict(entry)
            result[d["name"]] = d
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        return {k: dict(v) for k, v in spec.items() if v is not None} if spec else {}

    def diff(self, snap_spec: dict[str, Any], model_spec: dict[str, Any]) -> Tuple[List[Op], List[Op]]:
        up, rb = [], []
        snap, model = snap_spec or {}, model_spec or {}
        for name, info in model.items():
            if name not in snap:
                up.append(Op("create_ch_row_policy", {"name": name, **info}, {"name": name}))
                rb.insert(0, Op("drop_ch_row_policy", {"name": name}, {"name": name, **info}))
            else:
                si = snap[name]
                if si != info:
                    up.append(Op("alter_ch_row_policy", {"name": name, **info}, {"name": name, **si}))
                    rb.insert(0, Op("alter_ch_row_policy", {"name": name, **si}, {"name": name, **info}))
        for name in snap:
            if name not in model:
                si = snap[name]
                rb.insert(0, Op("create_ch_row_policy", {"name": name, **si}, {"name": name}))
                up.append(Op("drop_ch_row_policy", {"name": name}, {"name": name, **si}))
        return up, rb

    def emit(self, op: Op, db_name: Optional[str] = None, **kwargs: Any) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        name = op.upgrade_attrs["name"]
        if op.object_type == "create_ch_row_policy":
            table = op.upgrade_attrs.get("table", "")
            using = op.upgrade_attrs.get("using", "1 = 1")
            to_roles = op.upgrade_attrs.get("to_roles", ["ALL"])
            permissive = op.upgrade_attrs.get("permissive", True)
            kind = "PERMISSIVE" if permissive else "RESTRICTIVE"
            role_list = ", ".join(to_roles)
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"CREATE ROW POLICY IF NOT EXISTS {name} ON {table} FOR SELECT USING {using} AS {kind} TO {role_list};",
                rollback_sql=f"DROP ROW POLICY IF EXISTS {name} ON {table};",
            ))
        elif op.object_type == "drop_ch_row_policy":
            table = op.upgrade_attrs.get("table", "")
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"DROP ROW POLICY IF EXISTS {name} ON {table};",
                rollback_sql=f"-- Revert: CREATE ROW POLICY {name};",
            ))
        elif op.object_type == "alter_ch_row_policy":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"-- ALTER ROW POLICY {name};",
                rollback_sql=f"-- Revert ALTER ROW POLICY {name};",
            ))
        return stmts
