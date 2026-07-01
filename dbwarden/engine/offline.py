from __future__ import annotations

import json
from typing import Any

from dbwarden.engine.model_discovery import IndexInfo, ModelColumn, ModelTable
from dbwarden.engine.snapshot import (
    _check_ch_engine_recreate_allowed,
    _diff_ch_column_extras,
    _diff_ch_options,
    _index_op_from_info,
    _index_sig,
    _normalize_default,
    detect_renames,
    normalize_type,
    snap_to_model_key,
)

STATE_FORMAT_VERSION = 2


def model_state_to_dict(tables: list[ModelTable], dbwarden_version: str = "") -> dict:
    state_tables: dict[str, dict[str, Any]] = {}
    state_indexes: dict[str, dict[str, Any]] = {}
    state_constraints: dict[str, dict[str, Any]] = {}
    state_enums: dict[str, list[str]] = {}

    for table in tables:
        state_tables[table.name] = _table_to_state_entry(table)

        for idx in table.indexes:
            idx_dict = idx.to_dict() if hasattr(idx, "to_dict") else dict(idx)
            idx_name = idx_dict.get("name") or _generated_index_key(table.name, idx_dict)
            state_indexes[idx_name] = {"table": table.name, **idx_dict}

        for i, fk in enumerate(table.foreign_keys or []):
            state_constraints[_constraint_key(table.name, "foreign_key", i, fk.get("name"))] = {
                "type": "foreign_key",
                "table": table.name,
                "columns": list(fk.get("columns", [])),
                "referenced_table": fk.get("referenced_table") or fk.get("referred_table", ""),
                "referenced_columns": list(fk.get("referenced_columns", fk.get("referred_columns", []))),
                "on_delete": fk.get("on_delete", "NO ACTION"),
                "on_update": fk.get("on_update", "NO ACTION"),
                "deferrable": bool(fk.get("deferrable", False)),
            }

        for i, uq in enumerate(table.uniques or []):
            name = uq.get("name") or f"uq_{table.name}_{'_'.join(uq.get('columns', []))}"
            state_constraints[_constraint_key(table.name, "unique", i, name)] = {
                "type": "unique",
                "table": table.name,
                "name": name,
                **{k: _serialize_value(v) for k, v in uq.items() if k != "name"},
            }

        for i, ck in enumerate(table.checks or []):
            name = ck.get("name") or f"ck_{table.name}_{i}"
            state_constraints[_constraint_key(table.name, "check", i, name)] = {
                "type": "check",
                "table": table.name,
                "name": name,
                **{("expression" if k == "sql_expression" else k): _serialize_value(v) for k, v in ck.items() if k != "name"},
            }

        for i, ex in enumerate(table.excludes or table.pg_table.get("pg_excludes", []) or []):
            name = ex.get("name") or f"ex_{table.name}_{i}"
            state_constraints[_constraint_key(table.name, "exclude", i, name)] = {
                "type": "exclude",
                "table": table.name,
                "name": name,
                "expression": ex.get("expression", ""),
            }

        for col in table.columns:
            pg_type = (col.pg_meta or {}).get("pg_type", {})
            if pg_type.get("kind") == "enum":
                type_name = pg_type.get("type_name", "")
                if type_name:
                    state_enums[type_name] = list(pg_type.get("values", []))

    return {
        "format_version": STATE_FORMAT_VERSION,
        "exported_at": __import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dbwarden_version": dbwarden_version or "0.0.0",
        "tables": state_tables,
        "indexes": state_indexes,
        "constraints": state_constraints,
        "enums": state_enums,
    }


def normalize_model_state(state: dict[str, Any]) -> dict[str, Any]:
    format_version = int(state.get("format_version", 1) or 1)
    if format_version >= STATE_FORMAT_VERSION:
        return state

    tables = state.get("tables", {}) or {}
    normalized: dict[str, Any] = {
        "format_version": STATE_FORMAT_VERSION,
        "exported_at": state.get("exported_at"),
        "dbwarden_version": state.get("dbwarden_version", "0.0.0"),
        "tables": {},
        "indexes": {},
        "constraints": {},
        "enums": {},
    }

    for table_name, raw_table in tables.items():
        table_entry = dict(raw_table)
        columns = table_entry.get("columns", {}) or {}
        normalized_columns: dict[str, dict[str, Any]] = {}
        for col_name, col_entry in columns.items():
            normalized_col = dict(col_entry)
            normalized_col.setdefault("name", col_name)
            normalized_col.setdefault("autoincrement", None)
            pg_meta = normalized_col.pop("pg_meta", None) or normalized_col.get("pg_column") or {}
            ch_meta = normalized_col.pop("ch_meta", None) or normalized_col.get("ch_column") or {}
            my_meta = normalized_col.pop("my_meta", None) or normalized_col.get("my_column") or {}
            normalized_col["pg_column"] = {k: _serialize_value(v) for k, v in pg_meta.items()}
            normalized_col["ch_column"] = {k: _serialize_value(v) for k, v in ch_meta.items()}
            normalized_col["my_column"] = {k: _serialize_value(v) for k, v in my_meta.items()}

            pg_type = normalized_col["pg_column"].get("pg_type", {})
            if isinstance(pg_type, dict) and pg_type.get("kind") == "enum":
                type_name = pg_type.get("type_name", "")
                if type_name:
                    normalized["enums"][type_name] = list(pg_type.get("values", []))

            normalized_columns[col_name] = normalized_col

        backend_table_spec = table_entry.get("backend_table_spec", {}) or {}
        pg_excludes = list(backend_table_spec.get("pg_excludes", []) or [])
        normalized_table = {
            "name": table_name,
            "object_type": table_entry.get("object_type", "table"),
            "comment": table_entry.get("comment"),
            "backend": backend_table_spec.get("backend"),
            "backend_table_spec": backend_table_spec,
            "columns": normalized_columns,
        }
        normalized["tables"][table_name] = normalized_table

        for idx in table_entry.get("indexes", []) or []:
            idx_dict = idx if isinstance(idx, dict) else idx.to_dict()
            idx_name = idx_dict.get("name") or _generated_index_key(table_name, idx_dict)
            normalized["indexes"][idx_name] = {"table": table_name, **idx_dict}

        for i, fk in enumerate(table_entry.get("foreign_keys", []) or []):
            normalized["constraints"][_constraint_key(table_name, "foreign_key", i, fk.get("name"))] = {
                "type": "foreign_key",
                "table": table_name,
                "columns": list(fk.get("columns", fk.get("column", [] if fk.get("column") is None else [fk.get("column")]))),
                "referenced_table": fk.get("referenced_table") or fk.get("referred_table") or _parse_reference_table(fk.get("references")),
                "referenced_columns": list(fk.get("referenced_columns", fk.get("referred_columns", _parse_reference_columns(fk.get("references"))))),
                "on_delete": fk.get("on_delete", "NO ACTION"),
                "on_update": fk.get("on_update", "NO ACTION"),
                "deferrable": bool(fk.get("deferrable", False)),
            }

        for i, uq in enumerate(table_entry.get("uniques", []) or []):
            name = uq.get("name") or f"uq_{table_name}_{'_'.join(uq.get('columns', []))}"
            normalized["constraints"][_constraint_key(table_name, "unique", i, name)] = {
                "type": "unique",
                "table": table_name,
                "name": name,
                **{k: _serialize_value(v) for k, v in uq.items() if k != "name"},
            }

        for i, ck in enumerate(table_entry.get("checks", []) or []):
            name = ck.get("name") or f"ck_{table_name}_{i}"
            expression = ck.get("expression", ck.get("sql_expression", ""))
            normalized["constraints"][_constraint_key(table_name, "check", i, name)] = {
                "type": "check",
                "table": table_name,
                "name": name,
                "expression": expression,
                **{k: _serialize_value(v) for k, v in ck.items() if k not in {"name", "sql_expression"}},
            }

        for i, ex in enumerate(pg_excludes):
            name = ex.get("name") or f"ex_{table_name}_{i}"
            normalized["constraints"][_constraint_key(table_name, "exclude", i, name)] = {
                "type": "exclude",
                "table": table_name,
                "name": name,
                "expression": ex.get("expression", ""),
            }

    return normalized


def reconstruct_model_table(table_entry: dict[str, Any]) -> ModelTable:
    backend_spec = table_entry.get("backend_table_spec", {}) or {}
    indexes = [
        IndexInfo.from_dict(idx) if isinstance(idx, dict) else idx
        for idx in table_entry.get("indexes", []) or []
    ]
    columns = [reconstruct_model_column(col_entry) for _, col_entry in sorted((table_entry.get("columns", {}) or {}).items())]
    pg_table = {k: v for k, v in backend_spec.items() if k.startswith("pg_")}
    my_table = {k: v for k, v in backend_spec.items() if k.startswith("my_")}
    excludes = list(pg_table.get("pg_excludes", []) or [])
    return ModelTable(
        name=table_entry["name"],
        columns=columns,
        clickhouse_options={k: v for k, v in backend_spec.items() if k.startswith("ch_")},
        object_type=table_entry.get("object_type", "table"),
        foreign_keys=list(table_entry.get("foreign_keys", []) or []),
        indexes=indexes,
        comment=table_entry.get("comment"),
        checks=list(table_entry.get("checks", []) or []),
        uniques=list(table_entry.get("uniques", []) or []),
        excludes=excludes,
        pg_table=pg_table,
        my_table=my_table,
    )


def reconstruct_model_column(col_entry: dict[str, Any]) -> ModelColumn:
    return ModelColumn(
        name=col_entry["name"],
        type=col_entry.get("type", ""),
        nullable=col_entry.get("nullable", True),
        primary_key=col_entry.get("primary_key", False),
        unique=col_entry.get("unique", False),
        default=col_entry.get("default"),
        foreign_key=col_entry.get("foreign_key"),
        codec=(col_entry.get("ch_column", {}) or {}).get("ch_codec"),
        comment=col_entry.get("comment"),
        pg_meta=dict(col_entry.get("pg_column", {}) or {}),
        ch_meta=dict(col_entry.get("ch_column", {}) or {}),
        my_meta=dict(col_entry.get("my_column", {}) or {}),
        autoincrement=col_entry.get("autoincrement"),
    )


def _table_to_state_entry(table: ModelTable) -> dict[str, Any]:
    backend_table_spec: dict[str, Any] = {}
    ch_opts = table.clickhouse_options or {}
    if ch_opts:
        backend_table_spec["backend"] = "clickhouse"
        backend_table_spec.update({k: _serialize_value(v) for k, v in ch_opts.items() if k.startswith("ch_")})

    pg_table = table.pg_table or {}
    if pg_table:
        backend_table_spec["backend"] = "postgresql"
        backend_table_spec.update({k: _serialize_value(v) for k, v in pg_table.items() if v is not None})

    my_table = table.my_table or {}
    if my_table:
        backend_table_spec["backend"] = "mysql"
        backend_table_spec.update({k: _serialize_value(v) for k, v in my_table.items() if v is not None})

    return {
        "name": table.name,
        "columns": {col.name: _column_to_entry(col) for col in table.columns},
        "indexes": [idx.to_dict() if hasattr(idx, "to_dict") else idx for idx in table.indexes],
        "foreign_keys": [_serialize_value(fk) for fk in table.foreign_keys],
        "checks": [_serialize_value(ck) for ck in table.checks],
        "uniques": [_serialize_value(uq) for uq in table.uniques],
        "comment": table.comment,
        "object_type": table.object_type,
        "backend": backend_table_spec.get("backend"),
        "backend_table_spec": backend_table_spec,
    }


def _column_to_entry(col: Any) -> dict[str, Any]:
    return {
        "name": col.name,
        "type": col.type,
        "nullable": col.nullable,
        "primary_key": col.primary_key,
        "unique": col.unique,
        "default": col.default,
        "foreign_key": col.foreign_key,
        "comment": col.comment,
        "autoincrement": getattr(col, "autoincrement", None),
        "pg_column": {k: _serialize_value(v) for k, v in (getattr(col, "pg_meta", None) or {}).items() if v is not None},
        "ch_column": {k: _serialize_value(v) for k, v in (getattr(col, "ch_meta", None) or {}).items() if v is not None},
        "my_column": {k: _serialize_value(v) for k, v in (getattr(col, "my_meta", None) or {}).items() if v is not None},
    }


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


def _normalize_mysql_table_value(key: str, value: Any) -> Any:
    if value is None and key in {"my_auto_increment", "my_row_format"}:
        return None
    if isinstance(value, str) and key in {"my_engine", "my_charset", "my_collate", "my_row_format"}:
        return value.lower()
    return value


def _generated_index_key(table: str, idx: dict[str, Any]) -> str:
    cols = "_".join(idx.get("columns", [])) or "anon"
    unique = "uq" if idx.get("unique") else "idx"
    return f"{table}:{unique}:{cols}:{idx.get('using') or 'btree'}"


def _constraint_key(table: str, kind: str, index: int, name: str | None) -> str:
    return f"{table}:{kind}:{name or index}"


def _parse_reference_table(reference: Any) -> str:
    if not isinstance(reference, str) or "." not in reference:
        return ""
    return reference.split(".", 1)[0]


def _parse_reference_columns(reference: Any) -> list[str]:
    if not isinstance(reference, str) or "." not in reference:
        return []
    return [reference.split(".", 1)[1]]


def diff_model_states(prev_state: dict, curr_state: dict) -> tuple[list[dict], list[dict]]:
    prev_state = normalize_model_state(prev_state)
    curr_state = normalize_model_state(curr_state)

    prev_tables = prev_state.get("tables", {})
    curr_tables = curr_state.get("tables", {})
    prev_constraints = prev_state.get("constraints", {}) or {}
    curr_constraints = curr_state.get("constraints", {}) or {}
    prev_indexes = prev_state.get("indexes", {}) or {}
    curr_indexes = curr_state.get("indexes", {}) or {}
    prev_enums = prev_state.get("enums", {}) or {}
    curr_enums = curr_state.get("enums", {}) or {}

    upgrade_ops: list[dict] = []
    rollback_ops: list[dict] = []

    all_table_names = set(prev_tables.keys()) | set(curr_tables.keys())

    for table_name in sorted(all_table_names):
        prev_entry = prev_tables.get(table_name)
        curr_entry = curr_tables.get(table_name)

        if prev_entry is None and curr_entry is not None:
            upgrade_ops.append({
                "type": "create_table",
                "table": table_name,
                "object_type": curr_entry.get("object_type", "table"),
                "state_table": curr_entry,
                "severity": "INFO",
            })
            rollback_ops.append({
                "type": "drop_table",
                "table": table_name,
                "object_type": curr_entry.get("object_type", "table"),
                "state_table": curr_entry,
                "severity": "WARNING",
            })
            continue

        if curr_entry is None and prev_entry is not None:
            upgrade_ops.append({
                "type": "drop_table",
                "table": table_name,
                "object_type": prev_entry.get("object_type", "table"),
                "state_table": prev_entry,
                "severity": "WARNING",
            })
            rollback_ops.insert(0, {
                "type": "create_table",
                "table": table_name,
                "object_type": prev_entry.get("object_type", "table"),
                "state_table": prev_entry,
                "severity": "INFO",
            })
            continue

        prev_cols = prev_entry.get("columns", {})
        curr_cols = curr_entry.get("columns", {})
        prev_model_cols = {name: reconstruct_model_column(col) for name, col in prev_cols.items()}
        curr_model_cols = {name: reconstruct_model_column(col) for name, col in curr_cols.items()}

        dropped_cols = [(col_name, prev_cols[col_name]) for col_name in prev_cols if col_name not in curr_cols]
        added_cols = [(col_name, curr_model_cols[col_name]) for col_name in curr_model_cols if col_name not in prev_cols]
        renames = detect_renames(table_name, dropped_cols, added_cols)
        renamed_old = {old for old, _ in renames}
        renamed_new = {new for _, new in renames}

        for old_name, new_name in renames:
            upgrade_ops.append({"type": "rename_column", "table": table_name, "old_name": old_name, "new_name": new_name})
            rollback_ops.insert(0, {"type": "rename_column", "table": table_name, "old_name": new_name, "new_name": old_name})

        all_col_names = set(prev_cols.keys()) | set(curr_cols.keys())
        for col_name in sorted(all_col_names):
            if col_name in renamed_old or col_name in renamed_new:
                continue

            prev_col = prev_cols.get(col_name)
            curr_col = curr_cols.get(col_name)

            if prev_col is None and curr_col is not None:
                col_type = curr_col.get("type") or "???"
                upgrade_ops.append({
                    "type": "add_column", "table": table_name, "column": col_name,
                    "definition": {"type": col_type, "nullable": curr_col.get("nullable", True), "default": curr_col.get("default")},
                    "model_column": reconstruct_model_column(curr_col),
                    "severity": "INFO",
                })
                rollback_ops.insert(0, {
                    "type": "drop_column", "table": table_name, "column": col_name,
                    "definition": curr_col,
                    "severity": "WARNING",
                })
                continue

            if curr_col is None and prev_col is not None:
                col_type = prev_col.get("type") or "???"
                upgrade_ops.append({
                    "type": "drop_column", "table": table_name, "column": col_name,
                    "definition": prev_col,
                    "severity": "WARNING",
                })
                rollback_ops.insert(0, {
                    "type": "add_column", "table": table_name, "column": col_name,
                    "definition": {"type": col_type, "nullable": prev_col.get("nullable", True), "default": prev_col.get("default")},
                    "model_column": reconstruct_model_column(prev_col),
                    "severity": "INFO",
                })
                continue

            prev_type = prev_col.get("type", "")
            curr_type = curr_col.get("type", "")
            if _normalize_type(prev_type) != _normalize_type(curr_type):
                upgrade_ops.append({
                    "type": "alter_column_type", "table": table_name, "column": col_name,
                    "model_type": curr_type, "snap_type": prev_type,
                    "severity": "WARNING",
                })
                rollback_ops.insert(0, {
                    "type": "alter_column_type", "table": table_name, "column": col_name,
                    "model_type": prev_type, "snap_type": curr_type,
                    "severity": "WARNING",
                })

            if prev_col.get("nullable") != curr_col.get("nullable"):
                upgrade_ops.append({
                    "type": "alter_column_nullable", "table": table_name, "column": col_name,
                    "nullable": curr_col.get("nullable", True),
                    "col_type": curr_type,
                    "severity": "WARNING",
                })
                rollback_ops.insert(0, {
                    "type": "alter_column_nullable", "table": table_name, "column": col_name,
                    "nullable": prev_col.get("nullable", True),
                    "col_type": prev_type,
                    "severity": "WARNING",
                })

            if prev_col.get("autoincrement") is not None and bool(prev_col.get("autoincrement")) != bool(curr_col.get("autoincrement")):
                upgrade_ops.append({
                    "type": "alter_column_autoincrement", "table": table_name, "column": col_name,
                    "autoincrement": bool(curr_col.get("autoincrement")), "col_type": curr_type,
                    "nullable": curr_col.get("nullable"),
                })
                rollback_ops.insert(0, {
                    "type": "alter_column_autoincrement", "table": table_name, "column": col_name,
                    "autoincrement": bool(prev_col.get("autoincrement")), "col_type": prev_type,
                    "nullable": prev_col.get("nullable"),
                })

            if _normalize_default(prev_col.get("default")) != _normalize_default(curr_col.get("default")):
                upgrade_ops.append({
                    "type": "alter_column_default", "table": table_name, "column": col_name,
                    "default": curr_col.get("default"),
                    "severity": "INFO",
                })
                rollback_ops.insert(0, {
                    "type": "alter_column_default", "table": table_name, "column": col_name,
                    "default": prev_col.get("default"),
                    "severity": "INFO",
                })

            if prev_col.get("comment") != curr_col.get("comment"):
                upgrade_ops.append({
                    "type": "alter_column_comment", "table": table_name, "column": col_name,
                    "comment": curr_col.get("comment"),
                    "previous_comment": prev_col.get("comment"),
                    "col_type": curr_type,
                    "nullable": curr_col.get("nullable"),
                    "autoincrement": curr_col.get("autoincrement"),
                    "my_meta": curr_col.get("my_column", {}),
                    "severity": "INFO",
                })
                rollback_ops.insert(0, {
                    "type": "alter_column_comment", "table": table_name, "column": col_name,
                    "comment": prev_col.get("comment"),
                    "previous_comment": curr_col.get("comment"),
                    "col_type": prev_type,
                    "nullable": prev_col.get("nullable"),
                    "autoincrement": prev_col.get("autoincrement"),
                    "my_meta": prev_col.get("my_column", {}),
                    "severity": "INFO",
                })

            prev_pg_col = prev_col.get("pg_column", {}) or {}
            curr_pg_col = curr_col.get("pg_column", {}) or {}
            norm_prev_pg_col = {snap_to_model_key(k): v for k, v in prev_pg_col.items() if snap_to_model_key(k) not in ("pg_type",)}
            norm_curr_pg_col = {k: v for k, v in curr_pg_col.items() if k not in ("pg_type", "pg_enum_name", "pg_enum_values")}
            if norm_prev_pg_col != norm_curr_pg_col:
                upgrade_ops.append({
                    "type": "alter_pg_column_meta", "table": table_name, "column": col_name,
                    "col_type": curr_type, "snap_type": prev_type,
                    "from_pg_column": prev_pg_col, "to_pg_column": curr_pg_col,
                })
                rollback_ops.insert(0, {
                    "type": "alter_pg_column_meta", "table": table_name, "column": col_name,
                    "col_type": prev_type, "snap_type": curr_type,
                    "from_pg_column": curr_pg_col, "to_pg_column": prev_pg_col,
                })

            _diff_ch_column_extras(
                prev_col.get("ch_column", {}) or {},
                curr_col.get("ch_column", {}) or {},
                table_name,
                col_name,
                upgrade_ops,
                rollback_ops,
            )

            prev_my_col = prev_col.get("my_column", {}) or {}
            curr_my_col = curr_col.get("my_column", {}) or {}
            if prev_my_col != curr_my_col:
                upgrade_ops.append({
                    "type": "alter_my_column_meta", "table": table_name, "column": col_name,
                    "col_type": curr_type, "snap_type": prev_type,
                    "from_my_column": prev_my_col, "to_my_column": curr_my_col,
                    "nullable": curr_col.get("nullable", True),
                    "default": curr_col.get("default"),
                    "comment": curr_col.get("comment"),
                    "autoincrement": curr_col.get("autoincrement"),
                    "snap_nullable": prev_col.get("nullable", True),
                    "snap_default": prev_col.get("default"),
                    "snap_comment": prev_col.get("comment"),
                })
                rollback_ops.insert(0, {
                    "type": "alter_my_column_meta", "table": table_name, "column": col_name,
                    "col_type": prev_type, "snap_type": curr_type,
                    "from_my_column": curr_my_col, "to_my_column": prev_my_col,
                    "nullable": prev_col.get("nullable", True),
                    "default": prev_col.get("default"),
                    "comment": prev_col.get("comment"),
                    "autoincrement": prev_col.get("autoincrement"),
                    "snap_nullable": curr_col.get("nullable", True),
                    "snap_default": curr_col.get("default"),
                    "snap_comment": curr_col.get("comment"),
                })

        prev_spec = prev_entry.get("backend_table_spec", {}) or {}
        curr_spec = curr_entry.get("backend_table_spec", {}) or {}
        prev_ch_spec = prev_spec if prev_spec.get("backend") == "clickhouse" else {}
        curr_ch_spec = curr_spec if curr_spec.get("backend") == "clickhouse" else {}
        if prev_ch_spec.get("ch_engine") != curr_ch_spec.get("ch_engine") and prev_ch_spec.get("ch_engine") is not None and curr_ch_spec.get("ch_engine") is not None:
            _check_ch_engine_recreate_allowed(prev_ch_spec, curr_ch_spec, table_name)
            upgrade_ops.append({
                "type": "recreate_ch_table",
                "table": table_name,
                "reason": "ch_engine",
                "from_table": prev_entry,
                "to_table": curr_entry,
                "drop_old_after_swap": False,
                "preserve_old_suffix": "__dbw_old",
                "failed_suffix": "__dbw_failed",
            })
            rollback_ops.insert(0, {
                "type": "recreate_ch_table",
                "table": table_name,
                "reason": "ch_engine",
                "from_table": curr_entry,
                "to_table": prev_entry,
                "drop_old_after_swap": False,
                "preserve_old_suffix": "__dbw_failed",
                "failed_suffix": "__dbw_old",
            })
        else:
            _diff_ch_options(prev_ch_spec, curr_ch_spec, table_name, upgrade_ops, rollback_ops)

        prev_pg_table = prev_spec if prev_spec.get("backend") == "postgresql" else {}
        curr_pg_table = curr_spec if curr_spec.get("backend") == "postgresql" else {}
        scalar_keys = {k for k in set(prev_pg_table.keys()) | set(curr_pg_table.keys()) if k != "pg_excludes"}
        for key in sorted(scalar_keys):
            if prev_pg_table.get(key) != curr_pg_table.get(key):
                upgrade_ops.append({
                    "type": "alter_pg_table", "table": table_name, "key": key,
                    "from_value": prev_pg_table.get(key), "to_value": curr_pg_table.get(key),
                })
                rollback_ops.insert(0, {
                    "type": "alter_pg_table", "table": table_name, "key": key,
                    "from_value": curr_pg_table.get(key), "to_value": prev_pg_table.get(key),
                })

        prev_my_table = prev_spec if prev_spec.get("backend") == "mysql" else {}
        curr_my_table = curr_spec if curr_spec.get("backend") == "mysql" else {}
        scalar_keys = {k for k in set(prev_my_table.keys()) | set(curr_my_table.keys()) if k != "backend"}
        for key in sorted(scalar_keys):
            prev_val = _normalize_mysql_table_value(key, prev_my_table.get(key))
            curr_val = _normalize_mysql_table_value(key, curr_my_table.get(key))
            if key == "my_auto_increment" and curr_val is None:
                continue
            if prev_val != curr_val:
                upgrade_ops.append({
                    "type": "alter_my_table", "table": table_name, "key": key,
                    "from_value": prev_my_table.get(key), "to_value": curr_my_table.get(key),
                })
                rollback_ops.insert(0, {
                    "type": "alter_my_table", "table": table_name, "key": key,
                    "from_value": curr_my_table.get(key), "to_value": prev_my_table.get(key),
                })

        if prev_entry.get("comment") != curr_entry.get("comment"):
            upgrade_ops.append({
                "type": "alter_table_comment", "table": table_name,
                "comment": curr_entry.get("comment"),
                "previous_comment": prev_entry.get("comment"),
                "severity": "INFO",
            })
            rollback_ops.insert(0, {
                "type": "alter_table_comment", "table": table_name,
                "comment": prev_entry.get("comment"),
                "previous_comment": curr_entry.get("comment"),
                "severity": "INFO",
            })

    _diff_constraints(prev_tables, curr_tables, prev_constraints, curr_constraints, upgrade_ops, rollback_ops)
    _diff_indexes(prev_indexes, curr_indexes, upgrade_ops, rollback_ops)
    _diff_enums(prev_enums, curr_enums, upgrade_ops, rollback_ops)

    # --- Annotate recreate_ch_table ops with dependent MVs ---
    common_tables = set(prev_tables.keys()) & set(curr_tables.keys())
    for op in upgrade_ops + rollback_ops:
        if op.get("type") == "recreate_ch_table":
            tname = op["table"]
            mvs = sorted(
                en for en in common_tables
                if (prev_tables[en].get("backend_table_spec", {}) or {}).get("ch_to_table") == tname
                and (curr_tables[en].get("backend_table_spec", {}) or {}).get("ch_to_table") == tname
            )
            if mvs:
                op["dependent_mvs"] = mvs

    recreate_tables = {op["table"] for op in upgrade_ops if op.get("type") == "recreate_ch_table"}
    if recreate_tables:
        allowed = {"recreate_ch_table", "drop_table", "create_table", "rename_table", "alter_enum_add_value"}
        upgrade_ops = [op for op in upgrade_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]
        rollback_ops = [op for op in rollback_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]

    return upgrade_ops, rollback_ops


def _diff_constraints(
    prev_tables: dict[str, Any],
    curr_tables: dict[str, Any],
    prev_constraints: dict[str, Any],
    curr_constraints: dict[str, Any],
    upgrade_ops: list[dict[str, Any]],
    rollback_ops: list[dict[str, Any]],
) -> None:
    all_tables = sorted(set(prev_tables.keys()) | set(curr_tables.keys()))
    for table_name in all_tables:
        prev_uniques = {c["name"]: c for c in prev_constraints.values() if c.get("type") == "unique" and c.get("table") == table_name and c.get("name")}
        curr_uniques = {c["name"]: c for c in curr_constraints.values() if c.get("type") == "unique" and c.get("table") == table_name and c.get("name")}

        prev_by_cols = {frozenset(c.get("columns", [])): (name, c) for name, c in prev_uniques.items()}
        curr_by_cols = {frozenset(c.get("columns", [])): (name, c) for name, c in curr_uniques.items()}
        handled_prev: set[str] = set()
        handled_curr: set[str] = set()
        for cols_sig, (prev_name, prev_entry) in prev_by_cols.items():
            curr_match = curr_by_cols.get(cols_sig)
            if curr_match is None:
                continue
            curr_name, curr_entry = curr_match
            if prev_name == curr_name:
                handled_prev.add(prev_name)
                handled_curr.add(curr_name)
            elif prev_entry.get("columns") == curr_entry.get("columns"):
                upgrade_ops.append({"type": "rename_unique_constraint", "table": table_name, "old_name": prev_name, "new_name": curr_name, "columns": list(cols_sig)})
                rollback_ops.insert(0, {"type": "rename_unique_constraint", "table": table_name, "old_name": curr_name, "new_name": prev_name, "columns": list(cols_sig)})
                handled_prev.add(prev_name)
                handled_curr.add(curr_name)

        for name, uq in prev_uniques.items():
            if name in handled_prev:
                continue
            if name not in curr_uniques or prev_uniques[name] != curr_uniques[name]:
                payload = {k: v for k, v in uq.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "drop_unique_constraint", "table": table_name, "name": name, **payload})
                rollback_ops.insert(0, {"type": "add_unique_constraint", "table": table_name, "name": name, **payload})
        for name, uq in curr_uniques.items():
            if name in handled_curr:
                continue
            if name not in prev_uniques:
                payload = {k: v for k, v in uq.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "add_unique_constraint", "table": table_name, "name": name, **payload})
                rollback_ops.insert(0, {"type": "drop_unique_constraint", "table": table_name, "name": name, **payload})

        prev_checks = {c["name"]: c for c in prev_constraints.values() if c.get("type") == "check" and c.get("table") == table_name and c.get("name")}
        curr_checks = {c["name"]: c for c in curr_constraints.values() if c.get("type") == "check" and c.get("table") == table_name and c.get("name")}
        for name, ck in prev_checks.items():
            prev_sig = {k: v for k, v in ck.items() if k not in {"type", "table", "columns"}}
            curr_sig = {k: v for k, v in curr_checks.get(name, {}).items() if k not in {"type", "table", "columns"}}
            if name not in curr_checks or prev_sig != curr_sig:
                payload = {k: v for k, v in ck.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "drop_check_constraint", "table": table_name, "name": name, **payload})
                rollback_ops.insert(0, {"type": "add_check_constraint", "table": table_name, "name": name, **payload})
        for name, ck in curr_checks.items():
            if name not in prev_checks:
                payload = {k: v for k, v in ck.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "add_check_constraint", "table": table_name, "name": name, **payload})
                rollback_ops.insert(0, {"type": "drop_check_constraint", "table": table_name, "name": name, **payload})

        prev_excludes = {c["name"]: c for c in prev_constraints.values() if c.get("type") == "exclude" and c.get("table") == table_name and c.get("name")}
        curr_excludes = {c["name"]: c for c in curr_constraints.values() if c.get("type") == "exclude" and c.get("table") == table_name and c.get("name")}
        for name, ex in prev_excludes.items():
            if name not in curr_excludes or prev_excludes[name] != curr_excludes.get(name):
                upgrade_ops.append({"type": "drop_exclude_constraint", "table": table_name, "name": name, "expression": ex.get("expression", "")})
                rollback_ops.insert(0, {"type": "add_exclude_constraint", "table": table_name, "name": name, "expression": ex.get("expression", "")})
        for name, ex in curr_excludes.items():
            if name not in prev_excludes:
                upgrade_ops.append({"type": "add_exclude_constraint", "table": table_name, "name": name, "expression": ex.get("expression", "")})
                rollback_ops.insert(0, {"type": "drop_exclude_constraint", "table": table_name, "name": name, "expression": ex.get("expression", "")})

        prev_fks = [c for c in prev_constraints.values() if c.get("type") == "foreign_key" and c.get("table") == table_name]
        curr_fks = [c for c in curr_constraints.values() if c.get("type") == "foreign_key" and c.get("table") == table_name]

        def _fk_sig(fk: dict[str, Any]) -> tuple:
            return (
                frozenset(fk.get("columns", [])),
                fk.get("referenced_table") or fk.get("referred_table", ""),
                frozenset(fk.get("referenced_columns", fk.get("referred_columns", []))),
                fk.get("on_delete", "NO ACTION"),
                fk.get("on_update", "NO ACTION"),
                bool(fk.get("deferrable", False)),
            )

        prev_fk_sigs = {_fk_sig(fk) for fk in prev_fks}
        curr_fk_sigs = {_fk_sig(fk) for fk in curr_fks}
        for fk in prev_fks:
            if _fk_sig(fk) not in curr_fk_sigs:
                upgrade_ops.append({
                    "type": "drop_foreign_key", "table": table_name,
                    "columns": fk["columns"], "referenced_table": fk["referenced_table"], "referenced_columns": fk["referenced_columns"],
                })
                rollback_ops.insert(0, {
                    "type": "add_foreign_key", "table": table_name,
                    "columns": fk["columns"], "referenced_table": fk["referenced_table"], "referenced_columns": fk["referenced_columns"],
                    "on_delete": fk.get("on_delete", "NO ACTION"), "on_update": fk.get("on_update", "NO ACTION"), "deferrable": bool(fk.get("deferrable", False)),
                })
        for fk in curr_fks:
            if _fk_sig(fk) not in prev_fk_sigs:
                upgrade_ops.append({
                    "type": "add_foreign_key", "table": table_name,
                    "columns": fk["columns"], "referenced_table": fk["referenced_table"], "referenced_columns": fk["referenced_columns"],
                    "on_delete": fk.get("on_delete", "NO ACTION"), "on_update": fk.get("on_update", "NO ACTION"), "deferrable": bool(fk.get("deferrable", False)),
                })
                rollback_ops.insert(0, {
                    "type": "drop_foreign_key", "table": table_name,
                    "columns": fk["columns"], "referenced_table": fk["referenced_table"], "referenced_columns": fk["referenced_columns"],
                })


def _diff_indexes(prev_indexes: dict[str, Any], curr_indexes: dict[str, Any], upgrade_ops: list[dict[str, Any]], rollback_ops: list[dict[str, Any]]) -> None:
    prev_items = [(name, idx) for name, idx in prev_indexes.items()]
    curr_items = [(name, idx) for name, idx in curr_indexes.items()]
    prev_sigs = {_index_sig(idx): (name, idx) for name, idx in prev_items}
    curr_sigs = {_index_sig(idx): (name, idx) for name, idx in curr_items}

    for sig, (name, idx) in prev_sigs.items():
        if sig not in curr_sigs:
            upgrade_ops.append({
                "type": "drop_index", "table": idx["table"], "index_name": name,
                "columns": idx["columns"], "unique": idx.get("unique", False), "using": idx.get("using"),
                "where": idx.get("where"), "include": idx.get("include"), "with_params": idx.get("with_params"),
                "tablespace": idx.get("tablespace"), "nulls_not_distinct": idx.get("nulls_not_distinct", False),
                "column_sorting": idx.get("column_sorting"), "concurrently": idx.get("concurrently", True),
                "clickhouse_type": idx.get("clickhouse_type"), "clickhouse_granularity": idx.get("clickhouse_granularity"),
            })
            rollback_ops.insert(0, {
                "type": "add_index", "table": idx["table"], "columns": idx["columns"], "unique": idx.get("unique", False),
                "using": idx.get("using"), "where": idx.get("where"), "include": idx.get("include"), "with_params": idx.get("with_params"),
                "tablespace": idx.get("tablespace"), "nulls_not_distinct": idx.get("nulls_not_distinct", False),
                "column_sorting": idx.get("column_sorting"), "concurrently": idx.get("concurrently", True),
                "clickhouse_type": idx.get("clickhouse_type"), "clickhouse_granularity": idx.get("clickhouse_granularity"),
            })

    for sig, (_name, idx) in curr_sigs.items():
        if sig not in prev_sigs:
            upgrade_ops.append(_index_op_from_info(IndexInfo.from_dict(idx), idx["table"]))
            rollback_ops.insert(0, {"type": "drop_index", "table": idx["table"], "index_name": None, "columns": idx["columns"], "unique": idx.get("unique", False)})


def _diff_enums(prev_enums: dict[str, list[str]], curr_enums: dict[str, list[str]], upgrade_ops: list[dict[str, Any]], rollback_ops: list[dict[str, Any]]) -> None:
    for enum_name, curr_values in curr_enums.items():
        if enum_name not in prev_enums:
            upgrade_ops.append({"type": "create_type", "enum_name": enum_name, "values": curr_values})
            rollback_ops.insert(0, {"type": "drop_type", "enum_name": enum_name})

    for enum_name, prev_values in prev_enums.items():
        curr_values = curr_enums.get(enum_name)
        if curr_values is None:
            continue
        new_values = [v for v in curr_values if v not in prev_values]
        for v in new_values:
            idx = curr_values.index(v)
            after = curr_values[idx - 1] if idx > 0 else None
            upgrade_ops.append({"type": "alter_enum_add_value", "enum_name": enum_name, "value": v, "after": after})
            rollback_ops.insert(0, {"type": "alter_enum_add_value", "enum_name": enum_name, "value": v, "revert": True, "after": after})
