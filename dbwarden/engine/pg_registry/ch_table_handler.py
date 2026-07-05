from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.model_discovery import _format_clickhouse_expression
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
)


_CH_SETTING_KEYS: frozenset[str] = frozenset({
    "ch_settings",
    "ch_ttl",
    "ch_order_by",
    "ch_primary_key",
    "ch_partition_by",
    "ch_sample_by",
    "ch_engine",
    "ch_projections",
    "ch_select_statement",
    "ch_to_table",
    "ch_dictionary",
    "ch_dict_layout",
    "ch_dict_source",
    "ch_dict_lifetime",
    "ch_dict_primary_key",
    "ch_zookeeper_path",
    "ch_replica_name",
    "ch_object_type",
})

_CH_OPTION_KEYS: frozenset[str] = frozenset({
    "ch_engine",
    "ch_order_by",
    "ch_primary_key",
    "ch_partition_by",
    "ch_sample_by",
    "ch_ttl",
    "ch_settings",
    "ch_object_type",
    "ch_select_statement",
    "ch_to_table",
    "ch_dictionary",
    "ch_dict_layout",
    "ch_dict_source",
    "ch_dict_lifetime",
    "ch_dict_primary_key",
    "ch_zookeeper_path",
    "ch_replica_name",
    "ch_projections",
})

_RECREATE_REQUIRED_CH_KEYS: frozenset[str] = frozenset({
    "ch_select_statement",
    "ch_to_table",
    "ch_dictionary",
    "ch_dict_layout",
    "ch_dict_source",
    "ch_dict_lifetime",
    "ch_dict_primary_key",
    "ch_zookeeper_path",
    "ch_replica_name",
    "ch_object_type",
})


class ChTableHandler(ObjectHandler):
    object_type: str = "ch_table"
    op_types: tuple[str, ...] = ("alter_ch_options", "recreate_ch_table")
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.ALTER_TABLE_OPTIONS
    clickhouse_engine_recreate: bool = False

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for tname, tdata in snapshot.get("tables", {}).items():
            ch_opts = (
                tdata.get("ch_options")
                or tdata.get("clickhouse_options")
                or {}
            )
            if ch_opts:
                result[tname] = {
                    "ch_options": dict(ch_opts),
                    "snapshot_table": tdata,
                }
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for table in model_tables:
            if table.clickhouse_options:
                result[table.name] = {
                    "ch_options": dict(table.clickhouse_options),
                    "model_table": table,
                }
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
        from dbwarden.engine.snapshot import _check_ch_engine_recreate_allowed

        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        all_tables = set(snap_spec.keys()) | set(model_spec.keys())
        for tname in sorted(all_tables):
            snap_entry = snap_spec.get(tname, {})
            model_entry = model_spec.get(tname, {})
            snap_opts = snap_entry.get("ch_options", {})
            model_opts = model_entry.get("ch_options", {})
            if not snap_opts and not model_opts:
                continue

            snapshot_table = snap_entry.get("snapshot_table")
            model_table = model_entry.get("model_table")

            # Engine change -> recreate
            if (
                snap_opts.get("ch_engine") != model_opts.get("ch_engine")
                and snap_opts.get("ch_engine") is not None
                and model_opts.get("ch_engine") is not None
                and snapshot_table is not None
                and model_table is not None
            ):
                _check_ch_engine_recreate_allowed(snap_opts, model_opts, tname)
                from dbwarden.engine.offline import _table_to_state_entry

                from_dict = {
                    "name": tname,
                    **snapshot_table,
                    "backend_table_spec": {"backend": "clickhouse", **snap_opts},
                }
                to_dict = _table_to_state_entry(model_table)
                to_snap_dict = {
                    "name": tname,
                    **snapshot_table,
                    "backend_table_spec": {"backend": "clickhouse", **snap_opts},
                }
                upgrade_ops.append(Op(
                    object_type="recreate_ch_table",
                    upgrade_attrs={
                        "table": tname,
                        "reason": "ch_engine",
                        "from_table": from_dict,
                        "to_table": to_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_old",
                        "failed_suffix": "__dbw_failed",
                    },
                    rollback_attrs={
                        "table": tname,
                        "reason": "ch_engine",
                        "from_table": to_dict,
                        "to_table": to_snap_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_failed",
                        "failed_suffix": "__dbw_old",
                    },
                ))
                rollback_ops.append(Op(
                    object_type="recreate_ch_table",
                    upgrade_attrs={
                        "table": tname,
                        "reason": "ch_engine",
                        "from_table": to_dict,
                        "to_table": to_snap_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_failed",
                        "failed_suffix": "__dbw_old",
                    },
                    rollback_attrs={
                        "table": tname,
                        "reason": "ch_engine",
                        "from_table": from_dict,
                        "to_table": to_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_old",
                        "failed_suffix": "__dbw_failed",
                    },
                ))
                continue

            ch_changes: dict[str, dict[str, Any]] = {}
            for key in _CH_OPTION_KEYS:
                snap_val = snap_opts.get(key)
                model_val = model_opts.get(key)
                if json.dumps(snap_val, sort_keys=True, default=str) != json.dumps(model_val, sort_keys=True, default=str):
                    if snap_val is None and model_val is None:
                        continue
                    ch_changes[key] = {"from": snap_val, "to": model_val}

            has_recreate_keys = any(k in _RECREATE_REQUIRED_CH_KEYS for k in ch_changes)
            if has_recreate_keys and self.clickhouse_engine_recreate and snapshot_table is not None and model_table is not None:
                from dbwarden.engine.offline import _table_to_state_entry

                reason = ",".join(k for k in ch_changes if k in _RECREATE_REQUIRED_CH_KEYS)
                from_dict = {
                    "name": tname,
                    **snapshot_table,
                    "backend_table_spec": {"backend": "clickhouse", **snap_opts},
                }
                to_dict = _table_to_state_entry(model_table)
                to_snap_dict = {
                    "name": tname,
                    **snapshot_table,
                    "backend_table_spec": {"backend": "clickhouse", **snap_opts},
                }
                upgrade_ops.append(Op(
                    object_type="recreate_ch_table",
                    upgrade_attrs={
                        "table": tname,
                        "reason": reason,
                        "from_table": from_dict,
                        "to_table": to_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_old",
                        "failed_suffix": "__dbw_failed",
                    },
                    rollback_attrs={
                        "table": tname,
                        "reason": reason,
                        "from_table": to_dict,
                        "to_table": to_snap_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_failed",
                        "failed_suffix": "__dbw_old",
                    },
                ))
                rollback_ops.append(Op(
                    object_type="recreate_ch_table",
                    upgrade_attrs={
                        "table": tname,
                        "reason": reason,
                        "from_table": to_dict,
                        "to_table": to_snap_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_failed",
                        "failed_suffix": "__dbw_old",
                    },
                    rollback_attrs={
                        "table": tname,
                        "reason": reason,
                        "from_table": from_dict,
                        "to_table": to_dict,
                        "drop_old_after_swap": False,
                        "preserve_old_suffix": "__dbw_old",
                        "failed_suffix": "__dbw_failed",
                    },
                ))
                continue

            if ch_changes:
                upgrade_ops.append(Op(
                    object_type="alter_ch_options",
                    upgrade_attrs={
                        "table": tname,
                        "changes": ch_changes,
                    },
                    rollback_attrs={
                        "table": tname,
                        "changes": {k: {"from": v["to"], "to": v["from"]} for k, v in ch_changes.items()},
                    },
                ))
                rollback_ops.append(Op(
                    object_type="alter_ch_options",
                    upgrade_attrs={
                        "table": tname,
                        "changes": {k: {"from": v["to"], "to": v["from"]} for k, v in ch_changes.items()},
                    },
                    rollback_attrs={
                        "table": tname,
                        "changes": ch_changes,
                    },
                ))

        return upgrade_ops, rollback_ops

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.snapshot import _build_clickhouse_recreate_table_sql, _get_backend, _build_ch_projection_sql

        stmts: list[MigrationStatement] = []

        if op.object_type == "recreate_ch_table":
            return _build_clickhouse_recreate_table_sql(
                op.upgrade_attrs, db_name
            )

        if op.object_type == "alter_ch_options":
            changes_map = op.upgrade_attrs.get("changes", {})
            up_stmts: list[str] = []
            rb_stmts: list[str] = []
            table = op.upgrade_attrs["table"]
            for key, change in changes_map.items():
                to_val = change.get("to")
                from_val = change.get("from")
                if key == "ch_settings" and isinstance(to_val, dict):
                    for setting_key, setting_value in to_val.items():
                        up_stmts.append(f"ALTER TABLE {table} MODIFY SETTING {setting_key} = {setting_value}")
                    if isinstance(from_val, dict):
                        for setting_key, setting_value in from_val.items():
                            rb_stmts.append(f"ALTER TABLE {table} MODIFY SETTING {setting_key} = {setting_value}")
                elif key == "ch_ttl" and to_val:
                    ttl_sql = ", ".join(to_val) if isinstance(to_val, list) else str(to_val)
                    up_stmts.append(f"ALTER TABLE {table} MODIFY TTL {ttl_sql}")
                    if from_val:
                        prev_ttl = ", ".join(from_val) if isinstance(from_val, list) else str(from_val)
                        rb_stmts.append(f"ALTER TABLE {table} MODIFY TTL {prev_ttl}")
                elif key == "ch_order_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {table} MODIFY ORDER BY {_format_clickhouse_expression(to_val)}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {table} MODIFY ORDER BY {_format_clickhouse_expression(from_val)}")
                elif key == "ch_primary_key" and to_val:
                    up_stmts.append(f"ALTER TABLE {table} MODIFY PRIMARY KEY {_format_clickhouse_expression(to_val)}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {table} MODIFY PRIMARY KEY {_format_clickhouse_expression(from_val)}")
                elif key == "ch_partition_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {table} MODIFY PARTITION BY {to_val}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {table} MODIFY PARTITION BY {from_val}")
                elif key == "ch_sample_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {table} MODIFY SAMPLE BY {to_val}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {table} MODIFY SAMPLE BY {from_val}")
                elif key == "ch_engine":
                    up_stmts.append(f"-- ENGINE change for {table} requires table recreation")
                    rb_stmts.append(f"-- ENGINE change for {table} requires table recreation")
                elif key == "ch_projections":
                    _build_ch_projection_sql(table, to_val, from_val, up_stmts, rb_stmts)
                elif key in _RECREATE_REQUIRED_CH_KEYS:
                    up_stmts.append(f"-- {key} changed for {table}. Re-run with --clickhouse-engine-recreate to auto-generate recreation SQL.")
                    rb_stmts.append(f"-- {key} changed for {table}. Re-run with --clickhouse-engine-recreate to auto-generate recreation SQL.")

            if up_stmts or rb_stmts:
                stmts.append(MigrationStatement(
                    order=StatementOrder.ALTER_TABLE_OPTIONS,
                    upgrade_sql="\n".join(up_stmts) if up_stmts else "-- no-op",
                    rollback_sql="\n".join(rb_stmts) if rb_stmts else "-- no-op",
                ))

        return stmts
