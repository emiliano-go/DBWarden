from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class GrantsHandler(ObjectHandler):
    object_type: str = "grants"
    op_types: tuple[str, ...] = (
        "add_grant",
        "revoke_grant",
        "add_schema_grant",
        "revoke_schema_grant",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_PG_GRANT

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            grants = tdata.get("pg_grants", []) or []
            if grants:
                result[tname] = {_grant_key(g): g for g in grants}
        for sname, sg_list in snapshot.get("schema_grants", {}).items():
            for sg in sg_list:
                key = _grant_key(sg)
                result.setdefault(sname, {})[key] = {**sg, "_object_type": "SCHEMA"}
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            grants = table.pg_grants or []
            if grants:
                result[table.name] = {_grant_key(g): g for g in grants}
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        return spec

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        all_tables = set(snap_spec.keys()) | set(model_spec.keys())
        for tname in sorted(all_tables):
            snap_keys = snap_spec.get(tname, {})
            model_keys = model_spec.get(tname, {})

            for key, grant in model_keys.items():
                if key not in snap_keys:
                    obj_type = grant.pop("_object_type", "TABLE") if isinstance(grant, dict) else "TABLE"
                    if obj_type == "SCHEMA":
                        ot = "add_schema_grant"
                        ot_rb = "revoke_schema_grant"
                    else:
                        ot = "add_grant"
                        ot_rb = "revoke_grant"
                    upgrade_ops.append(Op(
                        object_type=ot,
                        upgrade_attrs={"table": tname, **grant, "_object_type": obj_type},
                        rollback_attrs={"table": tname, **grant, "_object_type": obj_type},
                    ))
                    rollback_ops.append(Op(
                        object_type=ot_rb,
                        upgrade_attrs={"table": tname, **grant, "_object_type": obj_type},
                        rollback_attrs={"table": tname, **grant, "_object_type": obj_type},
                    ))

            for key, grant in snap_keys.items():
                if key not in model_keys:
                    obj_type = grant.pop("_object_type", "TABLE") if isinstance(grant, dict) else "TABLE"
                    if obj_type == "SCHEMA":
                        ot = "revoke_schema_grant"
                        ot_rb = "add_schema_grant"
                    else:
                        ot = "revoke_grant"
                        ot_rb = "add_grant"
                    upgrade_ops.append(Op(
                        object_type=ot,
                        upgrade_attrs={"table": tname, **grant, "_object_type": obj_type},
                        rollback_attrs={"table": tname, **grant, "_object_type": obj_type},
                    ))
                    rollback_ops.append(Op(
                        object_type=ot_rb,
                        upgrade_attrs={"table": tname, **grant, "_object_type": obj_type},
                        rollback_attrs={"table": tname, **grant, "_object_type": obj_type},
                    ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import (
            _build_grant_sql,
            _build_revoke_sql,
            _qualified_name,
        )

        stmts: list[MigrationStatement] = []
        object_type = op.upgrade_attrs.get("_object_type", "TABLE")
        qname = (
            _qualified_name(op.upgrade_attrs["table"], op.upgrade_attrs.get("schema"))
            if object_type == "TABLE"
            else _qualified_name(op.upgrade_attrs["table"])
        )

        if op.object_type in ("add_grant", "add_schema_grant"):
            up = _build_grant_sql(op.upgrade_attrs, qname, object_type)
            rb = _build_revoke_sql(op.upgrade_attrs, qname, object_type)
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_GRANT,
                upgrade_sql=up, rollback_sql=rb,
            ))

        elif op.object_type in ("revoke_grant", "revoke_schema_grant"):
            up = _build_revoke_sql(op.upgrade_attrs, qname, object_type)
            rb = _build_grant_sql(op.upgrade_attrs, qname, object_type)
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_GRANT,
                upgrade_sql=up, rollback_sql=rb,
            ))

        return stmts


def _grant_key(g: dict) -> tuple:
    privs: tuple[str, ...]
    raw = g.get("privileges", ["ALL"])
    if isinstance(raw, list):
        privs = tuple(sorted(raw))
    else:
        privs = (raw,)
    return (g.get("role", "PUBLIC"), privs, bool(g.get("grantable", False)))
