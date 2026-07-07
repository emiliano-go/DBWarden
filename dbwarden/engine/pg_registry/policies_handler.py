from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class PoliciesHandler(ObjectHandler):
    object_type: str = "policies"
    op_types: tuple[str, ...] = (
        "alter_pg_rls",
        "add_policy",
        "drop_policy",
        "alter_policy",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_PG_POLICY

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            entry: dict[str, Any] = {}
            pg_table = tdata.get("pg_table") or tdata.get("backend_table_spec") or {}
            if pg_table.get("pg_rls"):
                entry["rls"] = True
            if pg_table.get("pg_rls_force"):
                entry["force"] = True
            policies = tdata.get("pg_policies", []) or []
            if policies:
                entry["policies"] = {p["name"]: p for p in policies}
            if entry:
                result[tname] = entry
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            entry: dict[str, Any] = {}
            pg_table = table.pg_table or {}
            if pg_table.get("pg_rls"):
                entry["rls"] = True
            if pg_table.get("pg_rls_force"):
                entry["force"] = True
            policies = table.pg_policies or []
            if policies:
                entry["policies"] = {p["name"]: p for p in policies}
            if entry:
                result[table.name] = entry
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        for entry in spec.values():
            if isinstance(entry, dict) and not entry.get("force"):
                entry.pop("force", None)
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
            snap_entry = snap_spec.get(tname, {})
            model_entry = model_spec.get(tname, {})

            snap_rls = snap_entry.get("rls", False) if isinstance(snap_entry, dict) else False
            model_rls = model_entry.get("rls", False) if isinstance(model_entry, dict) else False
            snap_force = snap_entry.get("force", False) if isinstance(snap_entry, dict) else False
            model_force = model_entry.get("force", False) if isinstance(model_entry, dict) else False
            if snap_rls != model_rls or snap_force != model_force:
                up_attrs: dict[str, Any] = {"table": tname, "enable": model_rls}
                rb_attrs: dict[str, Any] = {"table": tname, "enable": snap_rls}
                if model_force:
                    up_attrs["force"] = True
                if snap_force:
                    rb_attrs["force"] = True
                upgrade_ops.append(Op(
                    object_type="alter_pg_rls",
                    upgrade_attrs=up_attrs,
                    rollback_attrs=rb_attrs,
                ))
                rollback_ops.append(Op(
                    object_type="alter_pg_rls",
                    upgrade_attrs=rb_attrs,
                    rollback_attrs=up_attrs,
                ))

            snap_pols = snap_entry.get("policies", {}) if isinstance(snap_entry, dict) else {}
            model_pols = model_entry.get("policies", {}) if isinstance(model_entry, dict) else {}
            all_names = set(snap_pols.keys()) | set(model_pols.keys())
            for name in sorted(all_names):
                snap_pol = snap_pols.get(name)
                model_pol = model_pols.get(name)
                if snap_pol and not model_pol:
                    upgrade_ops.append(Op(
                        object_type="drop_policy",
                        upgrade_attrs={"table": tname, "name": name, **snap_pol},
                        rollback_attrs={"table": tname, "name": name, **snap_pol},
                    ))
                    rollback_ops.append(Op(
                        object_type="add_policy",
                        upgrade_attrs={"table": tname, "name": name, **snap_pol},
                        rollback_attrs={"table": tname, "name": name, **snap_pol},
                    ))
                elif model_pol and not snap_pol:
                    upgrade_ops.append(Op(
                        object_type="add_policy",
                        upgrade_attrs={"table": tname, "name": name, **model_pol},
                        rollback_attrs={"table": tname, "name": name, **model_pol},
                    ))
                    rollback_ops.append(Op(
                        object_type="drop_policy",
                        upgrade_attrs={"table": tname, "name": name, **model_pol},
                        rollback_attrs={"table": tname, "name": name, **model_pol},
                    ))
                elif model_pol != snap_pol:
                    cmd_changed = model_pol.get("command") != snap_pol.get("command")
                    permissive_changed = model_pol.get("permissive") != snap_pol.get("permissive")
                    if cmd_changed or permissive_changed:
                        upgrade_ops.append(Op(
                            object_type="add_policy",
                            upgrade_attrs={"table": tname, "name": name, **model_pol},
                            rollback_attrs={"table": tname, "name": name, **model_pol},
                        ))
                        upgrade_ops.append(Op(
                            object_type="drop_policy",
                            upgrade_attrs={"table": tname, "name": name, **snap_pol},
                            rollback_attrs={"table": tname, "name": name, **snap_pol},
                        ))
                        rollback_ops.append(Op(
                            object_type="add_policy",
                            upgrade_attrs={"table": tname, "name": name, **snap_pol},
                            rollback_attrs={"table": tname, "name": name, **snap_pol},
                        ))
                        rollback_ops.append(Op(
                            object_type="drop_policy",
                            upgrade_attrs={"table": tname, "name": name, **model_pol},
                            rollback_attrs={"table": tname, "name": name, **model_pol},
                        ))
                    else:
                        upgrade_ops.append(Op(
                            object_type="alter_policy",
                            upgrade_attrs={"table": tname, "name": name, **model_pol},
                            rollback_attrs={"table": tname, "name": name, **snap_pol},
                        ))
                        rollback_ops.append(Op(
                            object_type="alter_policy",
                            upgrade_attrs={"table": tname, "name": name, **snap_pol},
                            rollback_attrs={"table": tname, "name": name, **model_pol},
                        ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import (
            _build_alter_policy_sql,
            _build_create_policy_sql,
            _qualified_name,
            _quote_pg,
        )

        stmts: list[MigrationStatement] = []
        qname = _qualified_name(op.upgrade_attrs.get("table", ""), op.upgrade_attrs.get("schema"))
        table = op.upgrade_attrs["table"]

        if op.object_type == "alter_pg_rls":
            enable = op.upgrade_attrs.get("enable", False)
            force = op.upgrade_attrs.get("force", False)
            rb_enable = op.rollback_attrs.get("enable", False)
            rb_force = op.rollback_attrs.get("force", False)
            # Only emit force/no-force when the force flag actually changed
            force_changed = ("force" in op.upgrade_attrs) != ("force" in op.rollback_attrs)
            if enable:
                up = f"ALTER TABLE {qname} ENABLE ROW LEVEL SECURITY;"
                rb = f"ALTER TABLE {qname} DISABLE ROW LEVEL SECURITY;"
            else:
                up = f"ALTER TABLE {qname} DISABLE ROW LEVEL SECURITY;"
                rb = f"ALTER TABLE {qname} ENABLE ROW LEVEL SECURITY;"
            if force_changed:
                if force:
                    up += f"\nALTER TABLE {qname} FORCE ROW LEVEL SECURITY;"
                else:
                    up += f"\nALTER TABLE {qname} NO FORCE ROW LEVEL SECURITY;"
                if rb_force:
                    rb += f"\nALTER TABLE {qname} FORCE ROW LEVEL SECURITY;"
                else:
                    rb += f"\nALTER TABLE {qname} NO FORCE ROW LEVEL SECURITY;"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_RLS,
                upgrade_sql=up, rollback_sql=rb,
            ))

        elif op.object_type == "add_policy":
            up = _build_create_policy_sql(op.upgrade_attrs, qname)
            rb = f"DROP POLICY IF EXISTS {_quote_pg(op.upgrade_attrs['name'])} ON {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))

        elif op.object_type == "drop_policy":
            name = op.upgrade_attrs["name"]
            up = f"DROP POLICY IF EXISTS {_quote_pg(name)} ON {qname};"
            rb = f"-- Cannot auto-restore policy {name}; recreate from snapshot"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))

        elif op.object_type == "alter_policy":
            up = _build_alter_policy_sql(op.upgrade_attrs, qname)
            name = op.upgrade_attrs["name"]
            rb = f"-- Cannot auto-restore altered policy {name}; recreate from snapshot"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))

        return stmts
