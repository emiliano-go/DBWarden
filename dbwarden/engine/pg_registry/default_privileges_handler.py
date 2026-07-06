from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class DefaultPrivilegesHandler(ObjectHandler):
    object_type: str = "default_privileges"
    op_types: tuple[str, ...] = (
        "alter_default_privileges",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.ALTER_PG_GRANT

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("default_privileges", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_default_privileges", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            schema = entry.get("schema", "public")
            role = entry["role"]
            objtype = entry.get("object_type", "tables")
            privileges = entry.get("privileges", [])
            key = f"{schema}.{role}.{objtype}"
            spec[key] = {
                "schema": schema,
                "role": role,
                "object_type": objtype,
                "privileges": privileges,
            }
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
                    "schema": str(val.get("schema", "public")),
                    "role": str(val.get("role", "")),
                    "object_type": str(val.get("object_type", "tables")),
                }
                if val.get("privileges"):
                    if isinstance(val["privileges"], list):
                        entry["privileges"] = sorted(val["privileges"])
                    else:
                        entry["privileges"] = val["privileges"]
                if val.get("acl"):
                    entry["acl"] = str(val["acl"])
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

        all_keys = set(snap.keys()) | set(model.keys())
        for key in sorted(all_keys):
            snap_entry = snap.get(key)
            model_entry = model.get(key)

            if model_entry and not snap_entry:
                upgrade_ops.append(Op(
                    object_type="alter_default_privileges",
                    upgrade_attrs={
                        "schema": model_entry.get("schema", "public"),
                        "role": model_entry["role"],
                        "object_type": model_entry.get("object_type", "tables"),
                        "privileges": model_entry.get("privileges", []),
                    },
                    rollback_attrs={"key": key},
                ))
                rollback_ops.insert(0, Op(
                    object_type="alter_default_privileges",
                    upgrade_attrs={"key": key, "_revert": True},
                    rollback_attrs={
                        "schema": model_entry.get("schema", "public"),
                        "role": model_entry["role"],
                        "object_type": model_entry.get("object_type", "tables"),
                        "privileges": model_entry.get("privileges", []),
                    },
                ))
            elif model_entry and snap_entry:
                if model_entry.get("privileges") != snap_entry.get("privileges"):
                    upgrade_ops.append(Op(
                        object_type="alter_default_privileges",
                        upgrade_attrs={
                            "schema": model_entry.get("schema", "public"),
                            "role": model_entry["role"],
                            "object_type": model_entry.get("object_type", "tables"),
                            "privileges": model_entry.get("privileges", []),
                        },
                        rollback_attrs={
                            "schema": snap_entry.get("schema", "public"),
                            "role": snap_entry["role"],
                            "object_type": snap_entry.get("object_type", "tables"),
                            "privileges": snap_entry.get("privileges", []),
                        },
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="alter_default_privileges",
                        upgrade_attrs={
                            "schema": snap_entry.get("schema", "public"),
                            "role": snap_entry["role"],
                            "object_type": snap_entry.get("object_type", "tables"),
                            "privileges": snap_entry.get("privileges", []),
                        },
                        rollback_attrs={
                            "schema": model_entry.get("schema", "public"),
                            "role": model_entry["role"],
                            "object_type": model_entry.get("object_type", "tables"),
                            "privileges": model_entry.get("privileges", []),
                        },
                    ))

            if snap_entry and not model_entry:
                upgrade_ops.append(Op(
                    object_type="alter_default_privileges",
                    upgrade_attrs={
                        "schema": snap_entry.get("schema", "public"),
                        "role": snap_entry["role"],
                        "object_type": snap_entry.get("object_type", "tables"),
                        "privileges": [],
                        "_revert": True,
                    },
                    rollback_attrs={"key": key},
                ))
                rollback_ops.insert(0, Op(
                    object_type="alter_default_privileges",
                    upgrade_attrs={"key": key},
                    rollback_attrs={
                        "schema": snap_entry.get("schema", "public"),
                        "role": snap_entry["role"],
                        "object_type": snap_entry.get("object_type", "tables"),
                        "privileges": snap_entry.get("privileges", []),
                    },
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []

        if op.object_type == "alter_default_privileges":
            schema = op.upgrade_attrs.get("schema", "public")
            role = op.upgrade_attrs.get("role", "")
            objtype = op.upgrade_attrs.get("object_type", "tables")
            privs = op.upgrade_attrs.get("privileges", [])
            revert = op.upgrade_attrs.get("_revert", False)

            objtype_map = {
                "tables": "TABLES",
                "sequences": "SEQUENCES",
                "functions": "FUNCTIONS",
                "types": "TYPES",
                "schemas": "SCHEMAS",
            }
            pg_obj = objtype_map.get(objtype, "TABLES")

            if privs:
                priv_clause = ", ".join(p.upper() for p in (privs if isinstance(privs, list) else [privs]))
                up = f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT {priv_clause} ON {pg_obj} TO {role};"
                rb = f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE {priv_clause} ON {pg_obj} FROM {role};"
            elif revert:
                up = f"-- Revert default privileges for {role} on {objtype} in {schema}"
                rb = f"-- Restore default privileges for {role} on {objtype} in {schema}"
            else:
                up = f"-- Default privileges for {role} on {objtype} in {schema}; no privileges specified"
                rb = f"-- Revert default privileges for {role} on {objtype} in {schema}"

            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_GRANT,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
