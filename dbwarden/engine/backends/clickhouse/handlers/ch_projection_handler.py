from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.backends.clickhouse.cluster import emit_with_cluster
from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChProjectionHandler(ObjectHandler):
    """ClickHouse projection lifecycle: extract, diff, and emit DDL."""

    object_type: str = "ch_projection"
    op_types: tuple[str, ...] = ("alter_ch_projection",)
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_OPTIONS

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            ch_opts = (
                tdata.get("ch_options")
                or tdata.get("clickhouse_options")
                or {}
            )
            projs = ch_opts.get("ch_projections")
            if projs:
                result[tname] = list(projs)
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            ch_opts = table.clickhouse_options or {}
            projs = ch_opts.get("ch_projections")
            if projs:
                result[table.name] = list(projs)
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
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
            snap_projs: list[dict] = snap_spec.get(tname) or []
            model_projs: list[dict] = model_spec.get(tname) or []

            snap_by_name = {p.get("name", ""): p for p in snap_projs}
            model_by_name = {p.get("name", ""): p for p in model_projs}

            adds: list[dict] = []
            drops: list[str] = []
            replaces: list[tuple[str, str, str]] = []

            for name, snap_p in snap_by_name.items():
                if name not in model_by_name:
                    drops.append(name)

            for name, model_p in model_by_name.items():
                if name not in snap_by_name:
                    adds.append(model_p)
                else:
                    snap_p = snap_by_name[name]
                    if model_p.get("query") != snap_p.get("query"):
                        replaces.append((name, snap_p.get("query", ""), model_p.get("query", "")))

            if adds or drops or replaces:
                upgrade_attrs = {
                    "table": tname,
                    "add": [p for p in model_projs if p.get("name") in {a.get("name") for a in adds}],
                    "drop": drops,
                    "replace": replaces,
                }
                rollback_attrs = {
                    "table": tname,
                    "add": [p for p in snap_projs if p.get("name") in drops],
                    "drop": [a.get("name") for a in adds],
                    "replace": [(name, to_q, from_q) for name, from_q, to_q in replaces],
                }
                upgrade_ops.append(Op(
                    object_type="alter_ch_projection",
                    upgrade_attrs=upgrade_attrs,
                    rollback_attrs=rollback_attrs,
                ))
                rollback_ops.append(Op(
                    object_type="alter_ch_projection",
                    upgrade_attrs=rollback_attrs,
                    rollback_attrs=upgrade_attrs,
                ))

        return upgrade_ops, rollback_ops

    @emit_with_cluster
    def emit(
        self, op: Op, db_name: Optional[str] = None,
        **kwargs: Any,
    ) -> List[MigrationStatement]:
        from dbwarden.engine.backends.clickhouse.cluster import ClusterableStatement

        table = op.upgrade_attrs["table"]
        up_parts: list[str] = []
        rb_parts: list[str] = []

        for p in op.upgrade_attrs.get("add", []):
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD PROJECTION {p.get('name', '')} {p.get('query', '')}",
            ).render(self._cluster_ctx))
        for name in op.upgrade_attrs.get("drop", []):
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP PROJECTION {name}",
            ).render(self._cluster_ctx))
        for name, _from_q, to_q in op.upgrade_attrs.get("replace", []):
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP PROJECTION {name}",
            ).render(self._cluster_ctx))
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD PROJECTION {name} {to_q}",
            ).render(self._cluster_ctx))

        for p in op.rollback_attrs.get("add", []):
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD PROJECTION {p.get('name', '')} {p.get('query', '')}",
            ).render(self._cluster_ctx))
        for name in op.rollback_attrs.get("drop", []):
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP PROJECTION {name}",
            ).render(self._cluster_ctx))
        for name, from_q, _to_q in op.rollback_attrs.get("replace", []):
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP PROJECTION {name}",
            ).render(self._cluster_ctx))
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD PROJECTION {name} {from_q}",
            ).render(self._cluster_ctx))

        return [
            MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql="\n".join(up_parts) if up_parts else "-- no-op",
                rollback_sql="\n".join(rb_parts) if rb_parts else "-- no-op",
            )
        ]
