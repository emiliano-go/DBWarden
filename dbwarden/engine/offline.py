from __future__ import annotations

import json
from typing import Any

from dbwarden.engine.model_discovery import ModelTable


def model_state_to_dict(tables: list[ModelTable], dbwarden_version: str = "") -> dict:
    return {
        "format_version": 1,
        "exported_at": __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dbwarden_version": dbwarden_version or "0.0.0",
        "tables": {t.name: _table_to_state_entry(t) for t in tables},
    }


def _table_to_state_entry(table: ModelTable) -> dict:
    entry: dict[str, Any] = {
        "columns": {col.name: _column_to_entry(col) for col in table.columns},
        "indexes": [idx.to_dict() if hasattr(idx, "to_dict") else idx for idx in table.indexes],
        "foreign_keys": table.foreign_keys,
        "checks": table.checks,
        "uniques": table.uniques,
        "comment": table.comment,
        "object_type": table.object_type,
        "backend_table_spec": {},
    }

    ch_opts = table.clickhouse_options
    if ch_opts:
        entry["backend_table_spec"]["backend"] = "clickhouse"
        for k in ("ch_engine", "ch_order_by", "ch_primary_key", "ch_partition_by",
                  "ch_sample_by", "ch_ttl", "ch_settings", "ch_object_type",
                  "ch_select_statement", "ch_to_table", "ch_zookeeper_path",
                  "ch_replica_name", "ch_dictionary", "ch_dict_layout",
                  "ch_dict_source", "ch_dict_lifetime", "ch_dict_primary_key"):
            if k in ch_opts:
                entry["backend_table_spec"][k] = _serialize_value(ch_opts[k])

    pg_table = table.pg_table
    if pg_table:
        entry["backend_table_spec"]["backend"] = "postgresql"
        entry["backend_table_spec"].update({k: v for k, v in pg_table.items() if v is not None})

    return entry


def _column_to_entry(col: Any) -> dict:
    entry: dict[str, Any] = {
        "type": col.type,
        "nullable": col.nullable,
        "primary_key": col.primary_key,
        "unique": col.unique,
        "default": col.default,
        "foreign_key": col.foreign_key,
        "comment": col.comment,
    }
    ch_meta = getattr(col, "ch_meta", None) or {}
    if ch_meta:
        entry["ch_meta"] = {k: _serialize_value(v) for k, v in ch_meta.items() if v}
    pg_meta = getattr(col, "pg_meta", None) or {}
    if pg_meta:
        entry["pg_meta"] = {k: _serialize_value(v) for k, v in pg_meta.items() if v}
    return entry


def _serialize_value(val: Any) -> Any:
    if hasattr(val, "to_dict"):
        return val.to_dict()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, (list, tuple)):
        return [_serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    return val


def _normalize_type(t: str | None) -> str:
    if t is None:
        return ""
    return t.strip().lower().replace(" ", "").replace("(", "(").replace(")", ")")


def diff_model_states(prev_state: dict, curr_state: dict) -> tuple[list[dict], list[dict]]:
    prev_tables = prev_state.get("tables", {})
    curr_tables = curr_state.get("tables", {})

    upgrade_ops: list[dict] = []
    rollback_ops: list[dict] = []

    all_table_names = set(prev_tables.keys()) | set(curr_tables.keys())

    for table_name in sorted(all_table_names):
        prev_entry = prev_tables.get(table_name)
        curr_entry = curr_tables.get(table_name)

        if prev_entry is None and curr_entry is not None:
            upgrade_ops.append({"type": "create_table", "table": table_name, "severity": "INFO"})
            rollback_ops.append({"type": "drop_table", "table": table_name, "object_type": curr_entry.get("object_type", "table"), "severity": "WARNING"})
            continue

        if curr_entry is None and prev_entry is not None:
            upgrade_ops.append({"type": "drop_table", "table": table_name, "object_type": prev_entry.get("object_type", "table"), "severity": "WARNING"})
            rollback_ops.insert(0, {"type": "create_table", "table": table_name, "severity": "INFO"})
            continue

        prev_cols = prev_entry.get("columns", {})
        curr_cols = curr_entry.get("columns", {})

        all_col_names = set(prev_cols.keys()) | set(curr_cols.keys())

        for col_name in sorted(all_col_names):
            prev_col = prev_cols.get(col_name)
            curr_col = curr_cols.get(col_name)

            if prev_col is None and curr_col is not None:
                upgrade_ops.append({"type": "add_column", "table": table_name, "target": col_name, "severity": "INFO"})
                rollback_ops.insert(0, {"type": "drop_column", "table": table_name, "target": col_name, "severity": "WARNING"})
                continue

            if curr_col is None and prev_col is not None:
                upgrade_ops.append({"type": "drop_column", "table": table_name, "target": col_name, "severity": "WARNING"})
                rollback_ops.insert(0, {"type": "add_column", "table": table_name, "target": col_name, "severity": "INFO"})
                continue

            if _normalize_type(prev_col.get("type")) != _normalize_type(curr_col.get("type")):
                upgrade_ops.append({"type": "alter_column_type", "table": table_name, "target": col_name, "severity": "WARNING"})
                rollback_ops.insert(0, {"type": "alter_column_type", "table": table_name, "target": col_name, "severity": "WARNING"})

            if prev_col.get("nullable") != curr_col.get("nullable"):
                upgrade_ops.append({"type": "alter_column_nullable", "table": table_name, "target": col_name, "severity": "WARNING"})
                rollback_ops.insert(0, {"type": "alter_column_nullable", "table": table_name, "target": col_name, "severity": "WARNING"})

            if prev_col.get("default") != curr_col.get("default"):
                upgrade_ops.append({"type": "alter_column_default", "table": table_name, "target": col_name, "severity": "INFO"})
                rollback_ops.insert(0, {"type": "alter_column_default", "table": table_name, "target": col_name, "severity": "INFO"})

            if prev_col.get("comment") != curr_col.get("comment"):
                upgrade_ops.append({"type": "alter_comment", "table": table_name, "target": col_name, "severity": "INFO"})
                rollback_ops.insert(0, {"type": "alter_comment", "table": table_name, "target": col_name, "severity": "INFO"})

        # Index diff
        prev_idxs = {idx.get("name", ""): idx for idx in prev_entry.get("indexes", []) if idx.get("name")}
        curr_idxs = {idx.get("name", ""): idx for idx in curr_entry.get("indexes", []) if idx.get("name")}
        for name in set(prev_idxs.keys()) | set(curr_idxs.keys()):
            if name in curr_idxs and name not in prev_idxs:
                upgrade_ops.append({"type": "add_index", "table": table_name, "target": name, "severity": "INFO"})
                rollback_ops.insert(0, {"type": "drop_index", "table": table_name, "target": name, "severity": "WARNING"})
            elif name in prev_idxs and name not in curr_idxs:
                upgrade_ops.append({"type": "drop_index", "table": table_name, "target": name, "severity": "WARNING"})
                rollback_ops.insert(0, {"type": "add_index", "table": table_name, "target": name, "severity": "INFO"})

        # Comment diff
        if prev_entry.get("comment") != curr_entry.get("comment"):
            upgrade_ops.append({"type": "alter_comment", "table": table_name, "severity": "INFO"})
            rollback_ops.insert(0, {"type": "alter_comment", "table": table_name, "severity": "INFO"})

    return upgrade_ops, rollback_ops
