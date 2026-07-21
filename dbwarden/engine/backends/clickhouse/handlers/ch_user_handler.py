from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


def _create_user_sql(name: str, info: dict[str, Any]) -> str:
    auth = info.get("auth", "no_password")
    host = info.get("host", "ANY")
    parts = [f"CREATE USER IF NOT EXISTS {name} IDENTIFIED WITH {auth} HOST {host}"]
    roles = info.get("roles") or []
    if roles:
        parts.append(f"TO {', '.join(str(role) for role in roles)}")
    default_roles = info.get("default_roles") or []
    if default_roles:
        parts.append(f"DEFAULT ROLE {', '.join(str(role) for role in default_roles)}")
    profile = info.get("settings_profile")
    if profile:
        parts.append(f"SETTINGS PROFILE {profile}")
    return " ".join(parts) + ";"


def _drop_user_sql(name: str) -> str:
    return f"DROP USER IF EXISTS {name};"


class ChUserHandler(ObjectHandler):
    object_type: str = "ch_user"
    op_types: tuple[str, ...] = (
        "create_ch_user",
        "drop_ch_user",
        "alter_ch_user",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, info in snapshot.get("users", {}).items():
            if info.get("storage") == "users.xml":
                continue
            result[name] = {
                "name": name,
                "auth": info.get("auth", "no_password"),
                "roles": list(info.get("roles", [])),
                "default_roles": list(info.get("default_roles", [])),
                "host": info.get("host", "ANY"),
                "settings_profile": info.get("settings_profile"),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for entry in getattr(config, "ch_users", []) or []:
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
                up.append(Op("create_ch_user", {"name": name, **info}, {"name": name}))
                rb.insert(0, Op("drop_ch_user", {"name": name}, {"name": name, **info}))
            else:
                si = snap[name]
                stripped_model = {k: v for k, v in info.items() if k != "auth"}
                stripped_snap = {k: v for k, v in si.items() if k != "auth"}
                if stripped_model != stripped_snap:
                    up.append(Op("alter_ch_user", {"name": name, **info}, {"name": name, **si}))
                    rb.insert(0, Op("alter_ch_user", {"name": name, **si}, {"name": name, **info}))
        for name in snap:
            if name not in model:
                si = snap[name]
                rb.insert(0, Op("create_ch_user", {"name": name, **si}, {"name": name}))
                up.append(Op("drop_ch_user", {"name": name}, {"name": name, **si}))
        return up, rb

    def emit(self, op: Op, db_name: Optional[str] = None, **kwargs: Any) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        name = op.upgrade_attrs["name"]
        if op.object_type == "create_ch_user":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_create_user_sql(name, op.upgrade_attrs),
                rollback_sql=_drop_user_sql(name),
            ))
        elif op.object_type == "drop_ch_user":
            if "auth" in op.rollback_attrs or "host" in op.rollback_attrs:
                rollback_sql = _create_user_sql(name, op.rollback_attrs)
                rollback_kind = "real"
                rollback_reason = None
            else:
                rollback_sql = f"-- Revert: CREATE USER {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous ClickHouse user definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=_drop_user_sql(name),
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        elif op.object_type == "alter_ch_user":
            if "auth" in op.rollback_attrs or "host" in op.rollback_attrs:
                upgrade_sql = "\n".join([
                    _drop_user_sql(name),
                    _create_user_sql(name, op.upgrade_attrs),
                ])
                rollback_sql = "\n".join([
                    _drop_user_sql(name),
                    _create_user_sql(name, op.rollback_attrs),
                ])
                rollback_kind = "real"
                rollback_reason = None
            else:
                upgrade_sql = f"-- ALTER USER {name};"
                rollback_sql = f"-- Revert ALTER USER {name};"
                rollback_kind = "placeholder"
                rollback_reason = "previous ClickHouse user definition was not captured"
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
                rollback_kind=rollback_kind,
                rollback_reason=rollback_reason,
            ))
        return stmts
