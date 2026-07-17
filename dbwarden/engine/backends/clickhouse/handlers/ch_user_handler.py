from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


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
            auth = op.upgrade_attrs.get("auth", "no_password")
            roles = op.upgrade_attrs.get("roles", [])
            roles_clause = f" TO {', '.join(roles)}" if roles else ""
            host = op.upgrade_attrs.get("host", "ANY")
            profile = op.upgrade_attrs.get("settings_profile")
            profile_clause = f" SETTINGS PROFILE {profile}" if profile else ""
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"CREATE USER IF NOT EXISTS {name} IDENTIFIED WITH {auth} HOST {host}{roles_clause}{profile_clause};",
                rollback_sql=f"DROP USER IF EXISTS {name};",
            ))
        elif op.object_type == "drop_ch_user":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"DROP USER IF EXISTS {name};",
                rollback_sql=f"-- Revert: CREATE USER {name};",
            ))
        elif op.object_type == "alter_ch_user":
            roles = op.upgrade_attrs.get("roles", [])
            parts = [f"ALTER USER {name}"]
            if roles:
                parts.append(f"GRANTEES {', '.join(roles)}")
            host = op.upgrade_attrs.get("host")
            if host:
                parts.append(f"HOST {host}")
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"{' '.join(parts)};",
                rollback_sql=f"-- Revert ALTER USER {name};",
            ))
        return stmts
