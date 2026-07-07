from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class DomainHandler(ObjectHandler):
    """Handler for PostgreSQL DOMAIN types.

    Domains are declared in config (``pg_domains``, ``RunPhase.PREAMBLE``)
    and reverse-engineered into the snapshot by
    ``extract_full_schema_snapshot``.  The handler diffs snapshot vs
    model and emits delta DDL (``CREATE DOMAIN`` / ``DROP DOMAIN``).
    """

    object_type: str = "domain"
    op_types: tuple[str, ...] = (
        "create_domain",
        "drop_domain",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_DOMAIN

    # ------------------------------------------------------------------
    # Extract — read from snapshot
    # ------------------------------------------------------------------

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("domains", {}))

    # ------------------------------------------------------------------
    # Model spec (PREAMBLE path) — from config
    # ------------------------------------------------------------------

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_domains", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {
                "type": entry.get("type", "text"),
                "not_null": bool(entry.get("not_null", False)),
            }
            if entry.get("default"):
                info["default"] = entry["default"]
            if entry.get("check"):
                info["check"] = entry["check"]
            if entry.get("schema"):
                info["schema"] = entry["schema"]
            spec[name] = info
        return spec

    # ------------------------------------------------------------------
    # Model spec (DIFF path) — domains never come from tables
    # ------------------------------------------------------------------

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Canonicalize
    # ------------------------------------------------------------------

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for key, val in spec.items():
            if val is None:
                continue
            name = key.lower()
            if isinstance(val, dict):
                entry: dict[str, Any] = {
                    "type": str(val.get("domain_type", val.get("type", "text"))),
                    "not_null": bool(val.get("not_null", False)),
                }
                if val.get("default"):
                    entry["default"] = str(val["default"])
                if val.get("check"):
                    entry["check"] = str(val["check"])
                if val.get("schema"):
                    entry["schema"] = str(val["schema"])
                result[name] = entry
            else:
                result[name] = {"type": "text", "not_null": False}
        return result

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

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
                upgrade_ops.append(
                    Op(
                        object_type="create_domain",
                        upgrade_attrs={"domain_name": name, "domain_info": info},
                        rollback_attrs={"domain_name": name, "domain_info": info},
                    )
                )
                rollback_ops.insert(
                    0,
                    Op(
                        object_type="drop_domain",
                        upgrade_attrs={"domain_name": name, "domain_info": info},
                        rollback_attrs={"domain_name": name, "domain_info": info},
                    ),
                )
            else:
                snap_info = snap[name]
                if snap_info != info:
                    upgrade_ops.append(
                        Op(
                            object_type="create_domain",
                            upgrade_attrs={"domain_name": name, "domain_info": info},
                            rollback_attrs={"domain_name": name, "domain_info": snap_info},
                        )
                    )
                    rollback_ops.insert(
                        0,
                        Op(
                            object_type="drop_domain",
                            upgrade_attrs={"domain_name": name, "domain_info": snap_info},
                            rollback_attrs={"domain_name": name, "domain_info": snap_info},
                        ),
                    )

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(
                    0,
                    Op(
                        object_type="create_domain",
                        upgrade_attrs={"domain_name": name, "domain_info": snap_info},
                        rollback_attrs={"domain_name": name, "domain_info": snap_info},
                    ),
                )
                upgrade_ops.append(
                    Op(
                        object_type="drop_domain",
                        upgrade_attrs={"domain_name": name, "domain_info": snap_info},
                        rollback_attrs={"domain_name": name, "domain_info": snap_info},
                    )
                )

        return upgrade_ops, rollback_ops

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_domain":
            info = op.upgrade_attrs.get("domain_info", {})
            name = op.upgrade_attrs["domain_name"]
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            ddl_type = info.get("type", "text") if isinstance(info, dict) else "text"
            parts = [f"CREATE DOMAIN {qname} AS {ddl_type}"]
            if isinstance(info, dict):
                if info.get("default"):
                    parts.append(f"DEFAULT {info['default']}")
                if info.get("not_null"):
                    parts.append("NOT NULL")
                if info.get("check"):
                    parts.append(f"CHECK ({info['check']})")
            up = " ".join(parts) + ";"
            rb = f"DROP DOMAIN IF EXISTS {qname};"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_DOMAIN,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        elif op.object_type == "drop_domain":
            name = op.upgrade_attrs["domain_name"]
            schema = None
            info = op.upgrade_attrs.get("domain_info")
            if isinstance(info, dict):
                schema = info.get("schema")
            qname = _qualified_name(name, schema)
            up = f"DROP DOMAIN IF EXISTS {qname};"
            if isinstance(info, dict):
                ddl_type = info.get("type", "text")
                parts = [f"CREATE DOMAIN {qname} AS {ddl_type}"]
                if info.get("default"):
                    parts.append(f"DEFAULT {info['default']}")
                if info.get("not_null"):
                    parts.append("NOT NULL")
                if info.get("check"):
                    parts.append(f"CHECK ({info['check']})")
                rb = " ".join(parts) + ";"
            else:
                rb = f"-- Revert: CREATE DOMAIN {qname};"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_DOMAIN,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        return stmts
