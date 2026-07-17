from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChSettingsProfileHandler(ObjectHandler):
    object_type: str = "ch_settings_profile"
    op_types: tuple[str, ...] = (
        "create_ch_settings_profile",
        "drop_ch_settings_profile",
        "alter_ch_settings_profile",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, info in snapshot.get("settings_profiles", {}).items():
            if info.get("storage") == "users.xml":
                continue
            result[name] = {
                "name": name,
                "settings": dict(info.get("settings", {})),
                "to_roles": list(info.get("to_roles", [])),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for entry in getattr(config, "ch_settings_profiles", []) or []:
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
                up.append(Op("create_ch_settings_profile", {"name": name, **info}, {"name": name}))
                rb.insert(0, Op("drop_ch_settings_profile", {"name": name}, {"name": name, **info}))
            else:
                si = snap[name]
                if si.get("settings") != info.get("settings") or si.get("to_roles") != info.get("to_roles"):
                    up.append(Op("alter_ch_settings_profile", {"name": name, **info}, {"name": name, **si}))
                    rb.insert(0, Op("alter_ch_settings_profile", {"name": name, **si}, {"name": name, **info}))
        for name in snap:
            if name not in model:
                si = snap[name]
                rb.insert(0, Op("create_ch_settings_profile", {"name": name, **si}, {"name": name}))
                up.append(Op("drop_ch_settings_profile", {"name": name}, {"name": name, **si}))
        return up, rb

    def emit(self, op: Op, db_name: Optional[str] = None, **kwargs: Any) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        name = op.upgrade_attrs["name"]
        if op.object_type == "create_ch_settings_profile":
            settings = op.upgrade_attrs.get("settings", {})
            setting_clauses = ", ".join(f"{k}={v}" for k, v in settings.items())
            to_roles = op.upgrade_attrs.get("to_roles", [])
            roles_clause = f" TO {', '.join(to_roles)}" if to_roles else ""
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"CREATE SETTINGS PROFILE {name} SETTINGS {setting_clauses}{roles_clause};",
                rollback_sql=f"DROP SETTINGS PROFILE IF EXISTS {name};",
            ))
        elif op.object_type == "drop_ch_settings_profile":
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"DROP SETTINGS PROFILE IF EXISTS {name};",
                rollback_sql=f"-- Revert: CREATE SETTINGS PROFILE {name};",
            ))
        elif op.object_type == "alter_ch_settings_profile":
            settings = op.upgrade_attrs.get("settings", {})
            setting_clauses = ", ".join(f"{k}={v}" for k, v in settings.items())
            to_roles = op.upgrade_attrs.get("to_roles", [])
            roles_clause = f" TO {', '.join(to_roles)}" if to_roles else ""
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=f"ALTER SETTINGS PROFILE {name} SETTINGS {setting_clauses}{roles_clause};",
                rollback_sql=f"-- Revert ALTER SETTINGS PROFILE {name};",
            ))
        return stmts
