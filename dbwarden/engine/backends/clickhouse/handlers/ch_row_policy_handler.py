from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


def _row_policy_sql(name: str, info: dict[str, Any]) -> str:
    table = info.get("table", "")
    using = info.get("using") or "1 = 1"
    to_roles = info.get("to_roles") or ["ALL"]
    permissive = info.get("permissive", True)
    kind = "PERMISSIVE" if permissive else "RESTRICTIVE"
    role_list = ", ".join(str(role) for role in to_roles)
    return f"CREATE ROW POLICY IF NOT EXISTS {name} ON {table} FOR SELECT USING {using} AS {kind} TO {role_list};"


def _drop_row_policy_sql(name: str, table: str) -> str:
    return f"DROP ROW POLICY IF EXISTS {name} ON {table};"


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
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_row_policy_sql(name, op.upgrade_attrs),
                rollback_sql=_drop_row_policy_sql(name, table),
            ))
        elif op.object_type == "drop_ch_row_policy":
            table = op.upgrade_attrs.get("table", "")
            rb_table = op.rollback_attrs.get("table")
            if rb_table:
                rollback_sql = _row_policy_sql(name, op.rollback_attrs)
                rollback_kind = "real"
                rollback_reason = None
            else:
                rollback_sql = f"-- Revert: CREATE ROW POLICY {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous row policy definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_drop_row_policy_sql(name, table),
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        elif op.object_type == "alter_ch_row_policy":
            old_table = op.rollback_attrs.get("table")
            new_table = op.upgrade_attrs.get("table")
            if old_table and new_table:
                upgrade_sql = "\n".join([
                    _drop_row_policy_sql(name, old_table),
                    _row_policy_sql(name, op.upgrade_attrs),
                ])
                rollback_sql = "\n".join([
                    _drop_row_policy_sql(name, new_table),
                    _row_policy_sql(name, op.rollback_attrs),
                ])
                rollback_kind = "real"
                rollback_reason = None
            else:
                upgrade_sql = f"-- ALTER ROW POLICY {name};"
                rollback_sql = f"-- Revert ALTER ROW POLICY {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous row policy definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        return stmts
