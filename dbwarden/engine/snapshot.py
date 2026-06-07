from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

from dbwarden.engine.model_discovery import ModelColumn, ModelTable


TYPE_NORMALIZATION_MAP: dict[str, str | None] = {
    "int": "integer",
    "integer": "integer",
    "int4": "integer",
    "tinyint": "integer",
    "smallint": "integer",
    "int2": "integer",
    "bigint": "biginteger",
    "int8": "biginteger",
    "varchar": "varchar",
    "character varying": "varchar",
    "text": "text",
    "longtext": "text",
    "clob": "text",
    "mediumtext": "text",
    "boolean": "boolean",
    "bool": "boolean",
    "timestamp": "timestamp",
    "datetime": "timestamp",
    "date": "date",
    "float": "float",
    "real": "float",
    "double precision": "float",
    "double": "float",
    "numeric": "numeric",
    "decimal": "numeric",
    "json": "json",
    "jsonb": "json",
    "uuid": "uuid",
    "bytea": "bytes",
    "blob": "bytes",
    "binary": "bytes",
    "varbinary": "bytes",
    "enum": "enum",
}

_RAW_TYPE_PATTERN = re.compile(r"^([a-zA-Z][a-zA-Z0-9_]*)(?:\((\d+)(?:\s*,\s*(\d+))?\))?\s*$")


def normalize_type(raw_type: str) -> dict[str, Any]:
    raw_clean = raw_type.strip().lower()
    raw_no_parens = re.sub(r"\(.*?\)", "", raw_clean).strip()
    raw_no_parens_clean = re.sub(r"\s+", " ", raw_no_parens).strip()
    normalized = TYPE_NORMALIZATION_MAP.get(raw_no_parens_clean)
    if normalized is None:
        base = re.sub(r"[^a-z0-9]", "", raw_no_parens_clean) if raw_no_parens_clean else ""
        normalized = TYPE_NORMALIZATION_MAP.get(base)
    if normalized is None:
        base = re.sub(r"[^a-z]", "", raw_no_parens_clean) if raw_no_parens_clean else ""
        normalized = TYPE_NORMALIZATION_MAP.get(base)
    if normalized is not None:
        result: dict[str, Any] = {"type": normalized}
        full_lower = raw_type.strip().lower()
        length_match = re.search(r"\((\d+)\)", full_lower)
        if length_match and normalized in ("varchar",):
            result["length"] = int(length_match.group(1))
        precision_scale = re.search(r"\((\d+),\s*(\d+)\)", full_lower)
        if precision_scale and normalized in ("numeric",):
            result["precision"] = int(precision_scale.group(1))
            result["scale"] = int(precision_scale.group(2))
        return result
    fallback_match = _RAW_TYPE_PATTERN.match(raw_type.strip())
    if fallback_match:
        return {"type": raw_type.strip(), "raw": True}
    return {"type": raw_type.strip(), "raw": True}


def _is_autoincrement(column: dict[str, Any]) -> bool:
    type_str = str(column.get("type", "")).lower()
    if any(kw in type_str for kw in ("serial", "bigserial", "smallserial")):
        return True
    if column.get("autoincrement"):
        return True
    if column.get("primary_key") and type_str in ("integer", "bigint", "int", "smallint"):
        return True
    return False


def _get_generic_type_name(col_type: Any) -> str:
    type_str = str(col_type)
    if hasattr(col_type, "display_args") and hasattr(col_type, "as_generic"):
        try:
            generic = col_type.as_generic()
            if generic is not None:
                return str(generic)
        except Exception:
            pass
    return type_str


def extract_full_schema_snapshot(
    database: str | None = None,
    sqlalchemy_url: str | None = None,
    database_type: str | None = None,
) -> dict[str, Any]:
    from sqlalchemy import inspect, text

    db_name = database or "default"

    if sqlalchemy_url is not None and database_type is not None:
        from sqlalchemy import create_engine
        engine = create_engine(sqlalchemy_url)
        inspector = inspect(engine)
        own_engine = True
    else:
        from dbwarden.database.connection import get_db_connection
        conn_context = get_db_connection(database)
        connection = conn_context.__enter__()
        try:
            inspector = inspect(connection)
        except Exception:
            conn_context.__exit__(None, None, None)
            raise
        engine = None
        own_engine = False
        from dbwarden.config import get_database
        database_type = get_database(database).database_type

    tables: dict[str, Any] = {}
    enums: dict[str, Any] = {}
    indexes: dict[str, Any] = {}
    constraints: dict[str, Any] = {}

    for table_name in inspector.get_table_names():
        columns_info = inspector.get_columns(table_name)
        pk_info = inspector.get_pk_constraint(table_name)

        pk_columns = set(pk_info.get("constrained_columns", []) or [])

        columns_dict: dict[str, Any] = {}
        for col in columns_info:
            col_name = col["name"]
            col_type = col.get("type", "")
            raw_type_str = str(col_type)
            normalized = normalize_type(raw_type_str)
            col_type_name = normalized["type"]
            is_pk = col_name in pk_columns
            col_entry: dict[str, Any] = {
                "type": col_type_name,
                "nullable": bool(col.get("nullable", True)),
                "primary_key": is_pk,
                "default": col.get("default"),
                "autoincrement": _is_autoincrement(col),
            }
            if normalized.get("raw"):
                col_entry["raw"] = True
            if "length" in normalized:
                col_entry["length"] = normalized["length"]
            if "precision" in normalized:
                col_entry["precision"] = normalized["precision"]
            if "scale" in normalized:
                col_entry["scale"] = normalized["scale"]

            enum_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)$", raw_type_str)
            if database_type == "postgresql" and enum_match:
                with engine.connect() as conn:
                    result = conn.execute(
                        text(
                            "SELECT t.typname FROM pg_type t "
                            "JOIN pg_enum e ON t.oid = e.enumtypid "
                            "WHERE t.typname = :tname LIMIT 1"
                        ),
                        {"tname": raw_type_str},
                    )
                    if result.fetchone():
                        col_entry["enum_name"] = raw_type_str

            comment = col.get("comment")
            if comment is not None:
                col_entry["comment"] = comment

            columns_dict[col_name] = col_entry

        table_entry: dict[str, Any] = {
            "columns": columns_dict,
            "primary_key": list(pk_columns) if pk_columns else [],
            "comment": None,
        }

        if database_type == "postgresql":
            try:
                table_comment = inspector.get_table_comment(table_name)
                if table_comment and table_comment.get("text"):
                    table_entry["comment"] = table_comment["text"]
            except Exception:
                pass

        tables[table_name] = table_entry

        for idx in inspector.get_indexes(table_name):
            idx_name = idx.get("name", "")
            if not idx_name:
                continue
            if idx.get("unique") and set(idx.get("column_names", [])) == pk_columns:
                continue
            indexes[idx_name] = {
                "table": table_name,
                "columns": list(idx.get("column_names", [])),
                "unique": bool(idx.get("unique", False)),
                "type": idx.get("dialect_options", {}).get("sqlite_using", "btree"),
            }

        for fk in inspector.get_foreign_keys(table_name):
            fk_name = fk.get("name", "")
            if not fk_name:
                fk_name = f"fk_{table_name}_{'_'.join(fk.get('constrained_columns', []))}"
            constraints[fk_name] = {
                "type": "foreign_key",
                "table": table_name,
                "columns": list(fk.get("constrained_columns", [])),
                "referenced_table": fk.get("referred_table", ""),
                "referenced_columns": list(fk.get("referred_columns", [])),
                "on_delete": fk.get("options", {}).get("ondelete", "NO ACTION"),
                "on_update": fk.get("options", {}).get("onupdate", "NO ACTION"),
            }

        for uq in inspector.get_unique_constraints(table_name):
            uq_name = uq.get("name", "")
            if not uq_name:
                continue
            constraints[uq_name] = {
                "type": "unique",
                "table": table_name,
                "columns": list(uq.get("column_names", [])),
            }

        for ck in inspector.get_check_constraints(table_name):
            ck_name = ck.get("name", "")
            if not ck_name:
                ck_name = f"ck_{table_name}_{hash(ck.get('sqltext', ''))}"
            constraints[ck_name] = {
                "type": "check",
                "table": table_name,
                "columns": [],
                "expression": ck.get("sqltext", ""),
            }

    if database_type == "postgresql":
        try:
            for enum_info in inspector.get_enums():
                enums[enum_info["name"]] = list(enum_info.get("labels", []))
        except Exception:
            pass

    if own_engine and engine is not None:
        engine.dispose()
    else:
        try:
            conn_context.__exit__(None, None, None)
        except Exception:
            pass

    return {
        "format_version": 1,
        "migration_id": "",
        "database_name": db_name,
        "database_type": database_type or "",
        "applied_at": "",
        "tables": tables,
        "enums": enums,
        "indexes": indexes,
        "constraints": constraints,
    }


def compute_checksum(snapshot: dict[str, Any]) -> str:
    snapshot_copy = {k: v for k, v in snapshot.items() if k != "checksum"}
    raw = json.dumps(snapshot_copy, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_schemas_directory(database: str | None = None) -> str:
    base_dir = os.path.join(os.getcwd(), "dbwarden", "schemas")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def write_snapshot(
    snapshot: dict[str, Any],
    database: str | None = None,
    migration_id: str = "",
) -> str:
    from dbwarden.config import get_database

    config = get_database(database)
    db_name = database or config.sqlalchemy_url.split("/")[-1].split("?")[0]

    snapshot["migration_id"] = migration_id
    snapshot["database_name"] = db_name
    snapshot["database_type"] = config.database_type
    snapshot["applied_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    checksum = compute_checksum(snapshot)
    snapshot["checksum"] = checksum

    schemas_dir = get_schemas_directory(database)
    filename = f"{migration_id}.schema.json"
    filepath = os.path.join(schemas_dir, filename)

    fd, tmp_path = tempfile.mkstemp(dir=schemas_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)
            f.write("\n")
        os.replace(tmp_path, filepath)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise

    return filepath


def read_snapshot(filepath: str) -> dict[str, Any] | None:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    stored_checksum = snapshot.pop("checksum", None)
    if stored_checksum is not None:
        actual = compute_checksum(snapshot)
        snapshot["checksum"] = stored_checksum
        if actual != stored_checksum:
            return None
    else:
        snapshot["checksum"] = ""

    return snapshot


def find_latest_snapshot(database: str | None = None) -> dict[str, Any] | None:
    schemas_dir = get_schemas_directory(database)

    if not os.path.isdir(schemas_dir):
        return None

    db_name = database or "default"

    prefix = f"{db_name}__"
    candidates: list[tuple[str, str]] = []

    for fname in os.listdir(schemas_dir):
        if not fname.endswith(".schema.json"):
            continue
        if not fname.startswith(prefix):
            continue
        stem = fname[: -len(".schema.json")]
        migration_id = stem
        version_match = re.search(r"__(\d{4})_", migration_id)
        if version_match:
            version = version_match.group(1)
            candidates.append((version, os.path.join(schemas_dir, fname)))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    latest_path = candidates[-1][1]
    return read_snapshot(latest_path)


def extract_snapshot_tables(snapshot: dict[str, Any]) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for table_name, table_def in snapshot.get("tables", {}).items():
        tables[table_name] = set(table_def.get("columns", {}).keys())
    return tables


def detect_renames(
    table_name: str,
    dropped_columns: list[tuple[str, dict[str, Any]]],
    added_columns: list[tuple[str, ModelColumn]],
) -> list[tuple[str, str]]:
    renames: list[tuple[str, str]] = []

    if not dropped_columns or not added_columns:
        return renames

    dropped_by_type: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for col_name, col_def in dropped_columns:
        col_type = col_def.get("type", "")
        dropped_by_type.setdefault(col_type, []).append((col_name, col_def))

    added_by_type: dict[str, list[tuple[str, ModelColumn]]] = {}
    for col_name, model_col in added_columns:
        col_type = normalize_type(model_col.type)["type"]
        added_by_type.setdefault(col_type, []).append((col_name, model_col))

    used_dropped: set[str] = set()
    used_added: set[str] = set()

    for col_type in list(dropped_by_type.keys()):
        if col_type not in added_by_type:
            continue

        drops = dropped_by_type[col_type]
        adds = added_by_type[col_type]

        available_drops = [(n, d) for n, d in drops if n not in used_dropped]
        available_adds = [(n, m) for n, m in adds if n not in used_added]

        if not available_drops or not available_adds:
            continue

        if len(available_drops) == 1 and len(available_adds) == 1:
            drop_name = available_drops[0][0]
            add_name = available_adds[0][0]
            if drop_name != add_name:
                renames.append((drop_name, add_name))
                used_dropped.add(drop_name)
                used_added.add(add_name)
        elif len(available_drops) == len(available_adds):
            for drop_name, _ in available_drops:
                if drop_name not in used_dropped:
                    for add_name, _ in available_adds:
                        if add_name not in used_added:
                            renames.append((drop_name, add_name))
                            used_dropped.add(drop_name)
                            used_added.add(add_name)
                            break

    return renames


def diff_models_against_snapshot(
    model_tables: list[ModelTable],
    snapshot: dict[str, Any],
    database: str | None = None,
    db_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    snapshot_tables = snapshot.get("tables", {})
    model_by_name = {t.name: t for t in model_tables}

    for table in model_tables:
        if table.name not in snapshot_tables:
            upgrade_ops.append({
                "type": "create_table",
                "table": table.name,
                "sql": None,
            })
            rollback_ops.append({
                "type": "drop_table",
                "table": table.name,
            })

    for snap_table_name in snapshot_tables:
        if snap_table_name not in model_by_name:
            upgrade_ops.append({
                "type": "drop_table",
                "table": snap_table_name,
            })
            rollback_ops.append({
                "type": "create_table",
                "table": snap_table_name,
                "sql": None,
            })

    for table in model_tables:
        if table.name not in snapshot_tables:
            continue

        snap_columns = snapshot_tables[table.name].get("columns", {})
        model_columns = {c.name: c for c in table.columns}

        dropped_cols = []
        for col_name in snap_columns:
            if col_name not in model_columns:
                dropped_cols.append((col_name, snap_columns[col_name]))

        added_cols = []
        for col_name, model_col in model_columns.items():
            if col_name not in snap_columns:
                added_cols.append((col_name, model_col))

        renames = detect_renames(table.name, dropped_cols, added_cols)

        renamed_old = {old for old, _ in renames}
        renamed_new = {new for _, new in renames}

        for old_name, new_name in renames:
            upgrade_ops.append({
                "type": "rename_column",
                "table": table.name,
                "old_name": old_name,
                "new_name": new_name,
            })
            rollback_ops.append({
                "type": "rename_column",
                "table": table.name,
                "old_name": new_name,
                "new_name": old_name,
            })

        for col_name, col_def in dropped_cols:
            if col_name in renamed_old:
                continue
            upgrade_ops.append({
                "type": "drop_column",
                "table": table.name,
                "column": col_name,
            })
            rollback_ops.append({
                "type": "add_column",
                "table": table.name,
                "column": col_name,
                "definition": col_def,
            })

        for col_name, model_col in added_cols:
            if col_name in renamed_new:
                continue
            upgrade_ops.append({
                "type": "add_column",
                "table": table.name,
                "column": col_name,
                "model_column": model_col,
            })
            rollback_ops.append({
                "type": "drop_column",
                "table": table.name,
                "column": col_name,
            })

    return upgrade_ops, rollback_ops


def _apply_rename_intents(
    upgrade_ops: list[dict[str, Any]],
    rollback_ops: list[dict[str, Any]],
    confirmed_renames: set[tuple[str, str, str]],
    resolved_from_map: dict[tuple[str, str, str], str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Post-process diff ops to apply only the confirmed rename intents.

    confirmed_renames: set of (table, old_name, new_name) tuples.
    resolved_from_map: optional mapping from rename key to "rename_flag" / "prompt" / "auto_detected".

    - Rename_column ops NOT in the set → converted back to drop+add.
    - Drop+add pairs that match a confirmed rename → converted to rename_column.
    """
    confirmed_set: set[tuple[str, str, str]] = set()
    for table, old, new in confirmed_renames:
        confirmed_set.add((table, old, new))
    origin = resolved_from_map or {}

    rename_ops_by_key: dict[tuple[str, str, str], int] = {}
    for i, op in enumerate(upgrade_ops):
        if op["type"] == "rename_column":
            key = (op["table"], op["old_name"], op["new_name"])
            rename_ops_by_key[key] = i

    # Build tracking for drop+add pairs by table
    table_adds: dict[str, list[tuple[int, str]]] = {}
    table_drops: dict[str, list[tuple[int, str]]] = {}
    for i, op in enumerate(upgrade_ops):
        if op["type"] == "add_column":
            table_adds.setdefault(op["table"], []).append((i, op["column"]))
        elif op["type"] == "drop_column":
            table_drops.setdefault(op["table"], []).append((i, op["column"]))

    added_used: set[int] = set()
    dropped_used: set[int] = set()

    for table, old, new in sorted(confirmed_set, key=lambda x: (x[0], x[1], x[2])):
        key = (table, old, new)
        if key not in rename_ops_by_key:
            for drop_i, drop_col in table_drops.get(table, []):
                if drop_i in dropped_used or drop_col != old:
                    continue
                for add_i, add_col in table_adds.get(table, []):
                    if add_i in added_used or add_col != new:
                        continue
                    upgrade_ops[drop_i] = {
                        "type": "rename_column", "table": table,
                        "old_name": old, "new_name": new,
                        "resolved_from": origin.get(key),
                    }
                    upgrade_ops[add_i] = None
                    rollback_ops[drop_i] = {
                        "type": "rename_column", "table": table,
                        "old_name": new, "new_name": old,
                    }
                    rollback_ops[add_i] = None
                    added_used.add(add_i)
                    dropped_used.add(drop_i)
                    break
                break

    for key, op_i in rename_ops_by_key.items():
        table, old, new = key
        if (table, old, new) in confirmed_set:
            upgrade_ops[op_i]["resolved_from"] = origin.get(key)
        else:
            upgrade_ops[op_i] = {
                "type": "drop_column", "table": table,
                "column": old,
            }
            rollback_ops[op_i] = {
                "type": "add_column", "table": table,
                "column": old, "definition": {},
            }

    upgrade_ops = [op for op in upgrade_ops if op is not None]
    rollback_ops = [op for op in rollback_ops if op is not None]

    return upgrade_ops, rollback_ops


def snapshot_diff_to_sql(
    upgrade_ops: list[dict[str, Any]],
    rollback_ops: list[dict[str, Any]],
    database: str | None = None,
    db_name: str | None = None,
) -> tuple[str, str, list[Any]]:
    from dbwarden.engine.model_discovery import (
        generate_add_column_sql,
        generate_create_table_sql,
        generate_drop_object_sql,
    )
    from dbwarden.engine.migration_name import Change

    upgrade_parts: list[str] = []
    rollback_parts: list[str] = []
    changes: list[Change] = []

    for op in upgrade_ops:
        if op["type"] == "create_table":
            table = _find_model_table(op["table"], db_name=db_name)
            if table:
                sql = generate_create_table_sql(table, db_name)
                upgrade_parts.append(sql)
                changes.append(Change(operation="create_table", table=op["table"]))
            rollback_parts.append(generate_drop_object_sql(
                _find_model_table(op["table"], db_name=db_name) or ModelTable(name=op["table"], columns=[])
            ))
        elif op["type"] == "drop_table":
            upgrade_parts.append(f"DROP TABLE {op['table']}")
            rollback_parts.append(f"CREATE TABLE {op['table']} (/* restore from snapshot */)")
            changes.append(Change(operation="drop_table", table=op["table"]))
        elif op["type"] == "rename_column":
            upgrade_parts.append(f"ALTER TABLE {op['table']} RENAME COLUMN {op['old_name']} TO {op['new_name']}")
            rollback_parts.append(f"ALTER TABLE {op['table']} RENAME COLUMN {op['new_name']} TO {op['old_name']}")
            changes.append(Change(
                operation="rename_column", table=op["table"], target=op["new_name"],
                resolved_from=op.get("resolved_from"),
            ))
        elif op["type"] == "add_column":
            model_col = op.get("model_column")
            if model_col:
                sql = generate_add_column_sql(op["table"], model_col, db_name)
                upgrade_parts.append(sql)
            else:
                col_def = op.get("definition", {})
                upgrade_parts.append(
                    f"ALTER TABLE {op['table']} ADD COLUMN {op['column']} {col_def.get('type', '???')}"
                )
            rollback_parts.append(f"ALTER TABLE {op['table']} DROP COLUMN {op['column']}")
            changes.append(Change(operation="add_column", table=op["table"], target=op["column"]))
        elif op["type"] == "drop_column":
            upgrade_parts.append(f"ALTER TABLE {op['table']} DROP COLUMN {op['column']}")
            rollback_parts.append(f"ALTER TABLE {op['table']} ADD COLUMN {op['column']} {op.get('definition', {}).get('type', '???')}")
            changes.append(Change(operation="drop_column", table=op["table"], target=op["column"]))

    rollback_parts.reverse()
    return "\n\n".join(upgrade_parts), "\n\n".join(rollback_parts), changes


def _filter_duplicates_from_snapshot_diff(
    upgrade_sql: str,
    rollback_sql: str,
    changes: list[Any],
    existing_statements: set[str],
) -> tuple[str, str, list[Any]]:
    upgrade_parts = [s.strip() for s in upgrade_sql.split("\n\n") if s.strip()]
    rollback_parts = [s.strip() for s in rollback_sql.split("\n\n") if s.strip()]

    filtered_upgrade = []
    filtered_rollback = []
    filtered_changes = []

    for i, (up_sql, rb_sql) in enumerate(zip(upgrade_parts, rollback_parts)):
        if up_sql in existing_statements:
            continue
        filtered_upgrade.append(up_sql)
        filtered_rollback.append(rb_sql)
        if i < len(changes):
            filtered_changes.append(changes[i])

    return "\n\n".join(filtered_upgrade), "\n\n".join(filtered_rollback), filtered_changes


def _find_model_table(table_name: str, db_name: str | None = None) -> ModelTable | None:
    from dbwarden.config import get_database

    config = get_database(db_name)
    model_paths = config.model_paths
    if model_paths is None:
        from dbwarden.engine.model_discovery import auto_discover_model_paths
        model_paths = auto_discover_model_paths()
    if not model_paths:
        return None
    from dbwarden.engine.model_discovery import get_all_model_tables

    tables = get_all_model_tables(model_paths, db_name=db_name)
    for t in tables:
        if t.name == table_name:
            return t
    return None
