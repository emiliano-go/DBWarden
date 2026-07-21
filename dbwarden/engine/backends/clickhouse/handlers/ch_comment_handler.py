from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.backends.clickhouse.cluster import emit_with_cluster
from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class ChCommentHandler(ObjectHandler):
    object_type: str = "ch_comment"
    op_types: tuple[str, ...] = ("alter_ch_comment",)
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_COMMENT

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            if not tdata.get("ch_options"):
                continue
            table_comment = tdata.get("comment") or None
            columns: dict[str, Any] = {}
            for cname, cdata in tdata.get("columns", {}).items():
                col_comment = cdata.get("comment") or None
                if col_comment is not None:
                    columns[cname] = col_comment
            result[tname] = {
                "table_comment": table_comment,
                "columns": columns,
            }
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            ch_opts = getattr(table, "clickhouse_options", None) or {}
            if not ch_opts:
                continue
            table_comment = getattr(table, "comment", None) or None
            columns: dict[str, Any] = {}
            for col in getattr(table, "columns", []) or []:
                col_comment = getattr(col, "comment", None) or None
                if col_comment is not None:
                    columns[col.name] = col_comment
            result[table.name] = {
                "table_comment": table_comment,
                "columns": columns,
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, Any] = {}
        for tname, tdata in spec.items():
            if tdata is None:
                continue
            table_comment = tdata.get("table_comment") or None
            columns = {k: v for k, v in tdata.get("columns", {}).items() if v}
            result[tname] = {"table_comment": table_comment, "columns": columns}
        return result

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []
        all_tables = set(snap_spec.keys()) | set(model_spec.keys())
        for tname in sorted(all_tables):
            snap = snap_spec.get(tname, {}) or {}
            model = model_spec.get(tname, {}) or {}
            snap_table_comment = snap.get("table_comment")
            model_table_comment = model.get("table_comment")
            snap_columns = snap.get("columns", {}) or {}
            model_columns = model.get("columns", {}) or {}

            table_comment_change = snap_table_comment != model_table_comment
            all_cols = set(snap_columns.keys()) | set(model_columns.keys())
            col_changes: dict[str, tuple[str | None, str | None]] = {}
            for cname in all_cols:
                sc = snap_columns.get(cname)
                mc = model_columns.get(cname)
                if sc != mc:
                    col_changes[cname] = (sc, mc)

            if table_comment_change or col_changes:
                upgrade_attrs: dict[str, Any] = {
                    "table": tname,
                    "table_comment": model_table_comment,
                    "columns": dict(model_columns),
                }
                rollback_attrs: dict[str, Any] = {
                    "table": tname,
                    "table_comment": snap_table_comment,
                    "columns": dict(snap_columns),
                }
                upgrade_ops.append(Op("alter_ch_comment", upgrade_attrs, rollback_attrs))
                rollback_ops.append(Op("alter_ch_comment", rollback_attrs, upgrade_attrs))
        return upgrade_ops, rollback_ops

    @emit_with_cluster
    def emit(
        self, op: Op, db_name: Optional[str] = None,
        **kwargs: Any,
    ) -> List[MigrationStatement]:
        from dbwarden.engine.backends.clickhouse.cluster import ClusterableStatement

        table = op.upgrade_attrs["table"]
        parts: list[str] = []
        rb_parts: list[str] = []

        table_comment = op.upgrade_attrs.get("table_comment")
        snap_table_comment = op.rollback_attrs.get("table_comment")
        if table_comment != snap_table_comment:
            if table_comment:
                parts.append(f"COMMENT '{table_comment}'")
            else:
                parts.append("MODIFY COMMENT ''")
            if snap_table_comment:
                rb_parts.append(f"COMMENT '{snap_table_comment}'")

        model_columns = op.upgrade_attrs.get("columns", {}) or {}
        snap_columns = op.rollback_attrs.get("columns", {}) or {}
        all_cols = set(model_columns.keys()) | set(snap_columns.keys())
        for cname in sorted(all_cols):
            mc = model_columns.get(cname)
            sc = snap_columns.get(cname)
            if mc == sc:
                continue
            if mc is not None:
                parts.append(f"MODIFY COLUMN {cname} COMMENT '{mc}'")
            else:
                parts.append(f"MODIFY COLUMN {cname} REMOVE COMMENT")
            if sc is not None:
                rb_parts.append(f"MODIFY COLUMN {cname} COMMENT '{sc}'")
            else:
                rb_parts.append(f"MODIFY COLUMN {cname} REMOVE COMMENT")

        stmts: list[MigrationStatement] = []
        if parts:
            up_sql = "\n".join(
                ClusterableStatement(prefix=f"ALTER TABLE {table}", suffix=p).render(self._cluster_ctx)
                for p in parts
            )
            rb_sql = "\n".join(
                ClusterableStatement(prefix=f"ALTER TABLE {table}", suffix=p).render(self._cluster_ctx)
                for p in (rb_parts or ["-- no-op"])
            )
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=up_sql,
                rollback_sql=rb_sql,
            ))
        return stmts
