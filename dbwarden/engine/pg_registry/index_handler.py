from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class IndexHandler(ObjectHandler):
    object_type: str = "index"
    op_types: tuple[str, ...] = ("add_index", "drop_index")
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_INDEX

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot_indexes = snapshot.get("indexes", {})
        indexes_by_table: dict[str, list[dict[str, Any]]] = {}
        for key, idx in snapshot_indexes.items():
            t = idx.get("table")
            if t:
                indexes_by_table.setdefault(t, []).append(dict(idx))

        constraints: dict[str, dict[str, Any]] = {}
        for key, c in snapshot.get("constraints", {}).items():
            cname = c.get("name") or str(key).split(".", 1)[-1]
            constraints[cname] = dict(c)

        return {
            "indexes": indexes_by_table,
            "constraints": constraints,
            "snapshot_tables": set(snapshot.get("tables", {})),
        }

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        indexes_by_table: dict[str, list[Any]] = {}
        view_tables: set[str] = set()
        for table in model_tables:
            if table.object_type in ("view", "materialized_view"):
                view_tables.add(table.name)
                continue
            if table.indexes:
                indexes_by_table[table.name] = list(table.indexes)
        return {"indexes": indexes_by_table, "view_tables": view_tables}

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        from dbwarden.engine.snapshot import _index_sig

        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        snap_indexes = snap_spec.get("indexes", {})
        snap_constraints = snap_spec.get("constraints", {})
        snap_tables = snap_spec.get("snapshot_tables", set())
        model_indexes = model_spec.get("indexes", {})
        view_tables = model_spec.get("view_tables", set())

        all_tables = set(snap_indexes.keys()) | set(model_indexes.keys())
        for table_name in sorted(all_tables):
            if table_name not in snap_tables:
                continue
            if table_name in view_tables:
                continue

            model_idxs = model_indexes.get(table_name, [])
            model_sigs = {_index_sig(idx) for idx in model_idxs}

            snap_idxs = snap_indexes.get(table_name, [])
            snap_sigs = {_index_sig(idx) for idx in snap_idxs}

            for idx in snap_idxs:
                sig = _index_sig(idx)
                if sig not in model_sigs:
                    name = idx.get("name", "")
                    if idx.get("unique", False) and name:
                        c = snap_constraints.get(name)
                        if c and c.get("type") == "unique" and c.get("table") == table_name:
                            continue

                    upgrade_attrs: dict[str, Any] = {
                        "table": table_name,
                        "index_name": name,
                        "columns": idx["columns"],
                        "unique": idx.get("unique", False),
                        "using": idx.get("using"),
                        "where": idx.get("where"),
                        "include": idx.get("include"),
                        "with_params": idx.get("with_params"),
                        "tablespace": idx.get("tablespace"),
                        "nulls_not_distinct": idx.get("nulls_not_distinct", False),
                        "column_sorting": idx.get("column_sorting"),
                        "concurrently": idx.get("concurrently", True),
                        "clickhouse_type": idx.get("clickhouse_type"),
                        "clickhouse_granularity": idx.get("clickhouse_granularity"),
                        "postgresql_ops": idx.get("postgresql_ops"),
                        "expression": idx.get("expression"),
                    }
                    rollback_attrs: dict[str, Any] = {
                        "table": table_name,
                        "columns": idx["columns"],
                        "unique": idx.get("unique", False),
                        "using": idx.get("using"),
                        "where": idx.get("where"),
                        "include": idx.get("include"),
                        "with_params": idx.get("with_params"),
                        "tablespace": idx.get("tablespace"),
                        "nulls_not_distinct": idx.get("nulls_not_distinct", False),
                        "column_sorting": idx.get("column_sorting"),
                        "concurrently": idx.get("concurrently", True),
                        "clickhouse_type": idx.get("clickhouse_type"),
                        "clickhouse_granularity": idx.get("clickhouse_granularity"),
                        "postgresql_ops": idx.get("postgresql_ops"),
                        "expression": idx.get("expression"),
                    }
                    upgrade_ops.append(Op(
                        object_type="drop_index",
                        upgrade_attrs=upgrade_attrs,
                        rollback_attrs=rollback_attrs,
                    ))
                    rollback_ops.append(Op(
                        object_type="add_index",
                        upgrade_attrs=rollback_attrs,
                        rollback_attrs=upgrade_attrs,
                    ))

            for idx in model_idxs:
                sig = _index_sig(idx)
                if sig not in snap_sigs:
                    from dbwarden.engine.snapshot import _index_op_from_info
                    add_op = _index_op_from_info(idx, table_name)
                    rb_attrs = {
                        "table": table_name,
                        "index_name": None,
                        "columns": idx.columns,
                        "unique": idx.unique,
                        "using": idx.using,
                        "postgresql_ops": idx.postgresql_ops,
                    }
                    if idx.expression:
                        rb_attrs["expression"] = idx.expression
                    upgrade_ops.append(Op(
                        object_type="add_index",
                        upgrade_attrs=add_op,
                        rollback_attrs=rb_attrs,
                    ))
                    rollback_ops.append(Op(
                        object_type="drop_index",
                        upgrade_attrs=rb_attrs,
                        rollback_attrs=add_op,
                    ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.snapshot import _build_index_sql, _get_backend

        backend = _get_backend(db_name)
        op_dict: dict[str, Any] = {
            "type": op.object_type,
            **op.upgrade_attrs,
        }
        return _build_index_sql(op_dict, backend)
