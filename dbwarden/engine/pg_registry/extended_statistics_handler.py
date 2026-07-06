from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ExtendedStatisticsHandler(ObjectHandler):
    object_type: str = "extended_statistics"
    op_types: tuple[str, ...] = (
        "create_extended_statistics",
        "drop_extended_statistics",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_TYPE

    _KIND_MAP: dict[str, str] = {
        "d": "ndistinct",
        "f": "dependencies",
        "m": "mcv",
        "e": "expressions",
    }

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return dict(snapshot.get("extended_stats", {}))

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_extended_statistics", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {
                "table": entry["table"],
                "kinds": list(entry.get("kinds", [])),
                "columns": entry.get("columns") or None,
            }
            if entry.get("schema"):
                info["schema"] = entry["schema"]
            if entry.get("expressions"):
                info["expressions"] = entry["expressions"]
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
                entry: dict[str, Any] = {
                    "table": str(val.get("table", "")),
                    "kinds": sorted(val.get("kinds", [])),
                }
                if val.get("columns"):
                    entry["columns"] = str(val["columns"])
                if val.get("schema"):
                    entry["schema"] = str(val["schema"])
                if val.get("expressions"):
                    entry["expressions"] = list(val["expressions"])
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

        for name, info in model.items():
            if name not in snap:
                upgrade_ops.append(Op(
                    object_type="create_extended_statistics",
                    upgrade_attrs={"stat_name": name, "stat_info": info},
                    rollback_attrs={"stat_name": name, "stat_info": info},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_extended_statistics",
                    upgrade_attrs={"stat_name": name, "stat_info": info},
                    rollback_attrs={"stat_name": name, "stat_info": info},
                ))
            else:
                snap_info = snap[name]
                if snap_info != info:
                    upgrade_ops.append(Op(
                        object_type="create_extended_statistics",
                        upgrade_attrs={"stat_name": name, "stat_info": info},
                        rollback_attrs={"stat_name": name, "stat_info": snap_info},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="drop_extended_statistics",
                        upgrade_attrs={"stat_name": name, "stat_info": snap_info},
                        rollback_attrs={"stat_name": name, "stat_info": info},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_extended_statistics",
                    upgrade_attrs={"stat_name": name, "stat_info": snap_info},
                    rollback_attrs={"stat_name": name, "stat_info": snap_info},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_extended_statistics",
                    upgrade_attrs={"stat_name": name, "stat_info": snap_info},
                    rollback_attrs={"stat_name": name, "stat_info": snap_info},
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name, _quote_pg

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_extended_statistics":
            info = op.upgrade_attrs.get("stat_info", {})
            name = op.upgrade_attrs["stat_name"]
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            table_name = info.get("table", "") if isinstance(info, dict) else ""
            table_qname = _qualified_name(table_name, schema)
            kinds = info.get("kinds", []) if isinstance(info, dict) else []
            kind_str = ", ".join(
                self._KIND_MAP.get(k, k) for k in kinds if k in self._KIND_MAP
            )

            on_parts: list[str] = []
            columns = info.get("columns") if isinstance(info, dict) else None
            if columns:
                for c in columns.split(", "):
                    c = c.strip()
                    if c:
                        on_parts.append(_quote_pg(c))

            expressions = info.get("expressions") if isinstance(info, dict) else None
            if expressions:
                for expr in expressions:
                    on_parts.append(f"({ expr })")

            on_clause = ", ".join(on_parts) if on_parts else ""

            if kind_str:
                up = f"CREATE STATISTICS {qname} ({ kind_str }) ON { on_clause } FROM { table_qname };"
            else:
                up = f"CREATE STATISTICS {qname} ON { on_clause } FROM { table_qname };"

            rb = f"DROP STATISTICS IF EXISTS {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        elif op.object_type == "drop_extended_statistics":
            name = op.upgrade_attrs["stat_name"]
            schema = None
            info = op.upgrade_attrs.get("stat_info")
            if isinstance(info, dict):
                schema = info.get("schema")
            qname = _qualified_name(name, schema)
            up = f"DROP STATISTICS IF EXISTS {qname};"

            if isinstance(info, dict):
                table_name = info.get("table", "")
                table_qname = _qualified_name(table_name, schema)
                kinds = info.get("kinds", [])
                kind_str = ", ".join(
                    self._KIND_MAP.get(k, k) for k in kinds if k in self._KIND_MAP
                )
                on_parts: list[str] = []
                columns = info.get("columns")
                if columns:
                    for c in columns.split(", "):
                        c = c.strip()
                        if c:
                            on_parts.append(_quote_pg(c))
                expressions = info.get("expressions")
                if expressions:
                    for expr in expressions:
                        on_parts.append(f"({ expr })")
                on_clause = ", ".join(on_parts) if on_parts else ""
                if kind_str:
                    rb = f"CREATE STATISTICS {qname} ({ kind_str }) ON { on_clause } FROM { table_qname };"
                else:
                    rb = f"CREATE STATISTICS {qname} ON { on_clause } FROM { table_qname };"
            else:
                rb = f"-- Revert: CREATE STATISTICS {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.CREATE_TYPE,
                upgrade_sql=up,
                rollback_sql=rb,
            ))

        return stmts
