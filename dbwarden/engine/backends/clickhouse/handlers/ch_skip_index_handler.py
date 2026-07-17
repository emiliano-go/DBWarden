from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.backends.clickhouse.cluster import emit_with_cluster
from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChSkipIndexHandler(ObjectHandler):
    """ClickHouse data-skipping index lifecycle: extract, diff, and emit DDL."""

    object_type: str = "ch_skip_index"
    op_types: tuple[str, ...] = ("alter_ch_skip_index",)
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_INDEX

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            indexes = tdata.get("indexes") or []
            if indexes:
                result[tname] = list(indexes)
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            ch_opts = table.clickhouse_options or {}
            raw_indexes = ch_opts.get("ch_indexes") or []
            normalized: list[dict[str, Any]] = []
            for ix in raw_indexes:
                if hasattr(ix, "to_dict"):
                    normalized.append(ix.to_dict())
                elif isinstance(ix, dict):
                    d = dict(ix)
                    if "clickhouse_type" not in d and "type" in d:
                        d["clickhouse_type"] = d.pop("type")
                    if "clickhouse_granularity" not in d and "granularity" in d:
                        d["clickhouse_granularity"] = d.pop("granularity")
                    normalized.append(d)
                else:
                    normalized.append(dict(ix))
            if normalized:
                result[table.name] = normalized
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
            snap_indexes: list[dict] = snap_spec.get(tname) or []
            model_indexes: list[dict] = model_spec.get(tname) or []

            snap_by_name = {}
            for ix in snap_indexes:
                nm = ix.get("name", "")
                snap_by_name[nm] = {
                    "name": nm,
                    "columns": ix.get("columns", []),
                    "clickhouse_type": ix.get("clickhouse_type") or ix.get("type", "MINMAX"),
                    "clickhouse_granularity": ix.get("clickhouse_granularity") or ix.get("granularity", 1),
                    "expr": ix.get("expr"),
                }
            model_by_name = {}
            for ix in model_indexes:
                nm = ix.get("name", "")
                model_by_name[nm] = {
                    "name": nm,
                    "columns": ix.get("columns", []),
                    "clickhouse_type": ix.get("clickhouse_type") or ix.get("type", "MINMAX"),
                    "clickhouse_granularity": ix.get("clickhouse_granularity") or ix.get("granularity", 1),
                    "expr": ix.get("expr"),
                }

            adds: list[dict] = []
            drops: list[str] = []
            replaces: list[tuple[str, dict, dict]] = []

            for name, snap_ix in snap_by_name.items():
                if name not in model_by_name:
                    drops.append(name)

            for name, model_ix in model_by_name.items():
                if name not in snap_by_name:
                    adds.append(model_ix)
                else:
                    snap_ix = snap_by_name[name]
                    if (
                        model_ix["clickhouse_type"] != snap_ix["clickhouse_type"]
                        or model_ix["clickhouse_granularity"] != snap_ix["clickhouse_granularity"]
                        or model_ix.get("expr") != snap_ix.get("expr")
                        or model_ix.get("columns") != snap_ix.get("columns")
                    ):
                        replaces.append((name, snap_ix, model_ix))

            if adds or drops or replaces:
                upgrade_attrs = {
                    "table": tname,
                    "add": adds,
                    "drop": drops,
                    "replace": replaces,
                }
                rb_adds = [snap_by_name[n] for n in drops if n in snap_by_name]
                rb_drops = [a.get("name") for a in adds]
                rb_replaces = [(name, model_ix, snap_ix) for name, snap_ix, model_ix in replaces]
                rollback_attrs = {
                    "table": tname,
                    "add": rb_adds,
                    "drop": rb_drops,
                    "replace": rb_replaces,
                }
                upgrade_ops.append(Op(
                    object_type="alter_ch_skip_index",
                    upgrade_attrs=upgrade_attrs,
                    rollback_attrs=rollback_attrs,
                ))
                rollback_ops.append(Op(
                    object_type="alter_ch_skip_index",
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

        for ix in op.upgrade_attrs.get("add", []):
            cols = ", ".join(ix.get("columns", []))
            expr = ix.get("expr")
            col_expr = f"({expr})" if expr else f"({cols})"
            ix_type = ix.get("clickhouse_type", "MINMAX")
            granularity = ix.get("clickhouse_granularity", 1)
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD INDEX {ix.get('name', '')} {col_expr} TYPE {ix_type} GRANULARITY {granularity}",
            ).render(self._cluster_ctx))

        for name in op.upgrade_attrs.get("drop", []):
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP INDEX {name}",
            ).render(self._cluster_ctx))

        for _name, _snap_ix, model_ix in op.upgrade_attrs.get("replace", []):
            cols = ", ".join(model_ix.get("columns", []))
            expr = model_ix.get("expr")
            col_expr = f"({expr})" if expr else f"({cols})"
            ix_type = model_ix.get("clickhouse_type", "MINMAX")
            granularity = model_ix.get("clickhouse_granularity", 1)
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP INDEX {_name}",
            ).render(self._cluster_ctx))
            up_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD INDEX {_name} {col_expr} TYPE {ix_type} GRANULARITY {granularity}",
            ).render(self._cluster_ctx))

        for ix in op.rollback_attrs.get("add", []):
            cols = ", ".join(ix.get("columns", []))
            expr = ix.get("expr")
            col_expr = f"({expr})" if expr else f"({cols})"
            ix_type = ix.get("clickhouse_type", "MINMAX")
            granularity = ix.get("clickhouse_granularity", 1)
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD INDEX {ix.get('name', '')} {col_expr} TYPE {ix_type} GRANULARITY {granularity}",
            ).render(self._cluster_ctx))

        for name in op.rollback_attrs.get("drop", []):
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP INDEX {name}",
            ).render(self._cluster_ctx))

        for _name, snap_ix, _model_ix in op.rollback_attrs.get("replace", []):
            cols = ", ".join(snap_ix.get("columns", []))
            expr = snap_ix.get("expr")
            col_expr = f"({expr})" if expr else f"({cols})"
            ix_type = snap_ix.get("clickhouse_type", "MINMAX")
            granularity = snap_ix.get("clickhouse_granularity", 1)
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"DROP INDEX {_name}",
            ).render(self._cluster_ctx))
            rb_parts.append(ClusterableStatement(
                prefix=f"ALTER TABLE {table}",
                suffix=f"ADD INDEX {_name} {col_expr} TYPE {ix_type} GRANULARITY {granularity}",
            ).render(self._cluster_ctx))

        return [
            MigrationStatement(
                order=StatementOrder.ALTER_INDEX,
                upgrade_sql="\n".join(up_parts) if up_parts else "-- no-op",
                rollback_sql="\n".join(rb_parts) if rb_parts else "-- no-op",
            )
        ]
