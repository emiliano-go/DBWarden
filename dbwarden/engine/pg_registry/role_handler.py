from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class RoleHandler(ObjectHandler):
    object_type: str = "role"
    op_types: tuple[str, ...] = (
        "create_role",
        "drop_role",
        "alter_role",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("roles", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_roles", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {}
            for attr in ("superuser", "inherit", "createrole", "createdb", "login", "connlimit", "valid_until"):
                if attr in entry:
                    info[attr] = entry[attr]
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
                result[key] = dict(val)
            else:
                result[key] = {}
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
                    object_type="create_role",
                    upgrade_attrs={"role_name": name, "role_info": info},
                    rollback_attrs={"role_name": name},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_role",
                    upgrade_attrs={"role_name": name},
                    rollback_attrs={"role_name": name, "role_info": info},
                ))
            else:
                snap_info = snap[name]
                if snap_info != info:
                    upgrade_ops.append(Op(
                        object_type="alter_role",
                        upgrade_attrs={"role_name": name, "role_info": info},
                        rollback_attrs={"role_name": name, "role_info": snap_info},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="alter_role",
                        upgrade_attrs={"role_name": name, "role_info": snap_info},
                        rollback_attrs={"role_name": name, "role_info": info},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_role",
                    upgrade_attrs={"role_name": name, "role_info": snap_info},
                    rollback_attrs={"role_name": name},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_role",
                    upgrade_attrs={"role_name": name},
                    rollback_attrs={"role_name": name, "role_info": snap_info},
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        name = op.upgrade_attrs["role_name"]

        if op.object_type == "create_role":
            info = op.upgrade_attrs.get("role_info", {})
            parts = [f"CREATE ROLE {name}"]
            if isinstance(info, dict):
                if info.get("superuser"):
                    parts.append("SUPERUSER")
                if info.get("login"):
                    parts.append("LOGIN")
                if info.get("inherit", True) == False:
                    parts.append("NOINHERIT")
                if info.get("createrole"):
                    parts.append("CREATEROLE")
                if info.get("createdb"):
                    parts.append("CREATEDB")
                if info.get("connlimit"):
                    parts.append(f"CONNECTION LIMIT {info['connlimit']}")
                if info.get("valid_until"):
                    parts.append(f"VALID UNTIL '{info['valid_until']}'")
                if not any((info.get("superuser"), info.get("login"),
                            info.get("createrole"), info.get("createdb"),
                            info.get("connlimit"), info.get("valid_until"))):
                    parts.append("LOGIN")
            up = " ".join(parts) + ";"
            rb = f"DROP ROLE IF EXISTS {name};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_EXTENSION,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "drop_role":
            up = f"DROP ROLE IF EXISTS {name};"
            rb = f"-- Revert: CREATE ROLE {name};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_EXTENSION,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "alter_role":
            info = op.upgrade_attrs.get("role_info", {})
            parts = [f"ALTER ROLE {name}"]
            if isinstance(info, dict):
                if info.get("superuser"):
                    parts.append("SUPERUSER")
                elif "superuser" in info:
                    parts.append("NOSUPERUSER")
                if info.get("login"):
                    parts.append("LOGIN")
                elif "login" in info:
                    parts.append("NOLOGIN")
                if info.get("createrole"):
                    parts.append("CREATEROLE")
                elif "createrole" in info:
                    parts.append("NOCREATEROLE")
                if info.get("createdb"):
                    parts.append("CREATEDB")
                elif "createdb" in info:
                    parts.append("NOCREATEDB")
                if info.get("connlimit"):
                    parts.append(f"CONNECTION LIMIT {info['connlimit']}")
                if info.get("valid_until"):
                    parts.append(f"VALID UNTIL '{info['valid_until']}'")
            up = " ".join(parts) + ";"
            rb = f"-- Revert ALTER ROLE {name};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_EXTENSION,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
