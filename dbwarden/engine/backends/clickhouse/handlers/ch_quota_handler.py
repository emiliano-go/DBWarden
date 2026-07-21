from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


def _create_quota_sql(name: str, info: dict[str, Any]) -> str:
    interval = info.get("interval", "")
    limits = info.get("limits") or {}
    limit_clauses = ", ".join(f"{k} = {v}" for k, v in limits.items())
    to_roles = info.get("to_roles") or []
    roles_clause = f" TO {', '.join(str(role) for role in to_roles)}" if to_roles else ""
    interval_clause = f" FOR INTERVAL {interval}" if interval else ""
    limit_clause = f" {limit_clauses}" if limit_clauses else ""
    return f"CREATE QUOTA IF NOT EXISTS {name}{interval_clause}{limit_clause}{roles_clause};"


def _drop_quota_sql(name: str) -> str:
    return f"DROP QUOTA IF EXISTS {name};"


class ChQuotaHandler(ObjectHandler):
    object_type: str = "ch_quota"
    op_types: tuple[str, ...] = (
        "create_ch_quota",
        "drop_ch_quota",
        "alter_ch_quota",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, info in snapshot.get("quotas", {}).items():
            if info.get("storage") == "users.xml":
                continue
            result[name] = {
                "name": name,
                "interval": info.get("interval", ""),
                "limits": dict(info.get("limits", {})),
                "to_roles": list(info.get("to_roles", [])),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for entry in getattr(config, "ch_quotas", []) or []:
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
                up.append(Op("create_ch_quota", {"name": name, **info}, {"name": name}))
                rb.insert(0, Op("drop_ch_quota", {"name": name}, {"name": name, **info}))
            else:
                si = snap[name]
                if si != info:
                    up.append(Op("alter_ch_quota", {"name": name, **info}, {"name": name, **si}))
                    rb.insert(0, Op("alter_ch_quota", {"name": name, **si}, {"name": name, **info}))
        for name in snap:
            if name not in model:
                si = snap[name]
                rb.insert(0, Op("create_ch_quota", {"name": name, **si}, {"name": name}))
                up.append(Op("drop_ch_quota", {"name": name}, {"name": name, **si}))
        return up, rb

    def emit(self, op: Op, db_name: Optional[str] = None, **kwargs: Any) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        name = op.upgrade_attrs["name"]
        if op.object_type == "create_ch_quota":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_create_quota_sql(name, op.upgrade_attrs),
                rollback_sql=_drop_quota_sql(name),
            ))
        elif op.object_type == "drop_ch_quota":
            if "limits" in op.rollback_attrs or "interval" in op.rollback_attrs:
                rollback_sql = _create_quota_sql(name, op.rollback_attrs)
                rollback_kind = "real"
                rollback_reason = None
            else:
                rollback_sql = f"-- Revert: CREATE QUOTA {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous ClickHouse quota definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_drop_quota_sql(name),
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        elif op.object_type == "alter_ch_quota":
            if "limits" in op.rollback_attrs or "interval" in op.rollback_attrs:
                upgrade_sql = "\n".join([
                    _drop_quota_sql(name),
                    _create_quota_sql(name, op.upgrade_attrs),
                ])
                rollback_sql = "\n".join([
                    _drop_quota_sql(name),
                    _create_quota_sql(name, op.rollback_attrs),
                ])
                rollback_kind = "real"
                rollback_reason = None
            else:
                upgrade_sql = f"-- ALTER QUOTA {name} (quota changes);"
                rollback_sql = f"-- Revert ALTER QUOTA {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous ClickHouse quota definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        return stmts
