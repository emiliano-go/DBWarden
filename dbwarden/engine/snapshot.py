from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from dbwarden.engine.model_discovery import IndexInfo, ModelColumn, ModelTable


class StatementOrder(IntEnum):
    RENAME_TABLE = 0
    RENAME_COLUMN = 1
    ALTER_COLUMN_TYPE = 2
    ALTER_COLUMN_NULLABLE = 3
    ALTER_COLUMN_DEFAULT = 4
    CREATE_TABLE = 5
    ADD_COLUMN = 6
    ALTER_FOREIGN_KEY = 7
    ALTER_INDEX = 8
    DROP_COLUMN = 9
    DROP_TABLE = 10
    ALTER_TABLE_COMMENT = 11
    ALTER_COLUMN_COMMENT = 12
    ALTER_TABLE_OPTIONS = 13
    ALTER_TABLE_CONSTRAINT = 14
    ALTER_COLUMN_AUTOINCREMENT = 15


@dataclass
class TableRenameIntent:
    old_table: str
    new_table: str


@dataclass
class MigrationStatement:
    order: StatementOrder
    upgrade_sql: str
    rollback_sql: str


def _assemble_migration(
    statements: list[MigrationStatement],
) -> tuple[str, str]:
    upgrade_parts: list[str] = []
    rollback_parts: list[str] = []
    for stmt in sorted(statements, key=lambda s: s.order):
        upgrade_parts.append(stmt.upgrade_sql)
        rollback_parts.append(stmt.rollback_sql)
    rollback_parts.reverse()
    return "\n\n".join(upgrade_parts), "\n\n".join(rollback_parts)


def _get_backend(db_name: str | None = None) -> str:
    try:
        from dbwarden.config import get_database
        config = get_database(db_name)
        return config.database_type
    except Exception:
        return "sqlite"


TYPE_NORMALIZATION_MAP: dict[str, str | None] = {
    "int": "integer",
    "integer": "integer",
    "int4": "integer",
    "tinyint": "integer",
    "smallint": "integer",
    "int2": "integer",
    "bigint": "biginteger",
    "int8": "biginteger",
    "serial": "integer",
    "bigserial": "biginteger",
    "smallserial": "integer",
    "varchar": "varchar",
    "character varying": "varchar",
    "text": "text",
    "longtext": "text",
    "clob": "text",
    "mediumtext": "text",
    "boolean": "boolean",
    "bool": "boolean",
    "timestamp": "timestamp",
    "timestamptz": "timestamptz",
    "timestamp with time zone": "timestamptz",
    "datetime": "timestamp",
    "date": "date",
    "float": "float",
    "float32": "float32",
    "real": "float32",
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
    "tsvector": "tsvector",
    "tstzrange": "tstzrange",
    "tsrange": "tsrange",
    "daterange": "daterange",
    "int4range": "int4range",
    "int8range": "int8range",
    "numrange": "numrange",
    # ClickHouse native type mappings (non-conflicting with PG names)
    "float64": "float",
    "string": "varchar",
    "fixedstring": "varchar",
    "datetime64": "timestamp",
    "date32": "date",
    "ipv4": "varchar",
    "ipv6": "varchar",
    "map": "map",
    "enum8": "enum",
    "enum16": "enum",
    "tuple": "tuple",
}

_RAW_TYPE_PATTERN = re.compile(r"^([a-zA-Z][a-zA-Z0-9_]*)(?:\((\d+)(?:\s*,\s*(\d+))?\))?\s*$")


def _strip_ch_type_wrappers(raw_type: str) -> str:
    """Strip Nullable() and LowCardinality() wrappers from a CH type string."""
    result = raw_type.strip()
    while result.startswith("Nullable(") and result.endswith(")"):
        result = result[9:-1].strip()
    while result.startswith("LowCardinality(") and result.endswith(")"):
        result = result[15:-1].strip()
    return result


def _model_type_str(sa_type) -> str:
    """Render a SQLAlchemy type to a string suitable for comparing with snapshot types.

    Handles Enum types correctly (str() returns VARCHAR without dialect context).
    """
    if hasattr(sa_type, "enums") and sa_type.enums:
        return f"Enum({', '.join(repr(v) for v in sa_type.enums)})"
    return str(sa_type)


@functools.lru_cache(maxsize=512)
def normalize_type(raw_type: str) -> dict[str, Any]:
    # Strip COLLATE clause for normalization purposes
    raw_type = re.sub(r'\s+COLLATE\s+"[^"]*"', "", raw_type, flags=re.IGNORECASE)
    raw_type = re.sub(r"\s+COLLATE\s+'[^']*'", "", raw_type, flags=re.IGNORECASE)
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
        if normalized == "timestamptz":
            result["type"] = "timestamp"
            result["has_timezone"] = True
        if normalized == "float32":
            result["type"] = "float"
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


def _build_alter_type_sql(
    table: str,
    column: str,
    new_type: str,
    backend: str,
    old_type: str | None = None,
    postgres_auto_using: bool = False,
) -> tuple[str, str]:
    if old_type:
        rollback_type = old_type
        rollback_comment = ""
    else:
        rollback_type = _missing_def_placeholder(backend)
        rollback_comment = "-- "

    if backend == "postgresql":
        upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type}"
        if postgres_auto_using:
            upgrade += f" USING {column}::{new_type}"
        else:
            upgrade += f"\n-- USING {column}::{new_type}"
        rollback = f"{rollback_comment}ALTER TABLE {table} ALTER COLUMN {column} TYPE {rollback_type}"
    elif backend in ("mysql", "mariadb"):
        _assert_complete_mysql_type(new_type)
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {new_type}"
        if old_type:
            _assert_complete_mysql_type(old_type)
        rollback = f"{rollback_comment}ALTER TABLE {table} MODIFY COLUMN {column} {rollback_type}"
    elif backend == "sqlite":
        upgrade = (
            f"-- SQLite does not support ALTER COLUMN TYPE.\n"
            f"-- Use 'dbwarden new' to write a manual migration for:\n"
            f"-- ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type}"
        )
        rollback = f"{rollback_comment}ALTER TABLE {table} ALTER COLUMN {column} TYPE {rollback_type}"
    elif backend == "clickhouse":
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {new_type}"
        rollback = f"{rollback_comment}ALTER TABLE {table} MODIFY COLUMN {column} {rollback_type}"
    else:
        upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {new_type}"
        rollback = f"{rollback_comment}ALTER TABLE {table} ALTER COLUMN {column} TYPE {rollback_type}"
    return upgrade, rollback


def _build_alter_nullable_sql(
    table: str,
    column: str,
    nullable: bool,
    col_type: str,
    backend: str,
) -> tuple[str, str]:
    if backend == "postgresql":
        if nullable:
            upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
            rollback = f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"
        else:
            upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"
            rollback = f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
    elif backend in ("mysql", "mariadb"):
        _assert_complete_mysql_type(col_type)
        null_clause = "NULL" if nullable else "NOT NULL"
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type} {null_clause}"
        rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type} {'NOT NULL' if nullable else 'NULL'}"
    elif backend == "sqlite":
        upgrade = f"-- SQLite: ALTER TABLE {table} ALTER COLUMN {column} {'DROP' if nullable else 'SET'} NOT NULL (not supported)"
        rollback = f"-- SQLite: ALTER TABLE {table} ALTER COLUMN {column} {'SET' if nullable else 'DROP'} NOT NULL (not supported)"
    else:
        if nullable:
            upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
            rollback = f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"
        else:
            upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL"
            rollback = f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
    return upgrade, rollback


def _build_alter_default_sql(
    table: str,
    column: str,
    default: Any,
    backend: str,
    col_type: str | None = None,
    nullable: bool | None = None,
    my_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    if backend in ("mysql", "mariadb"):
        return _build_mysql_alter_default_sql(
            table, column, default,
            col_type=col_type, nullable=nullable, my_meta=my_meta or {},
        )
    if default is not None:
        safe_default = _quote_default_for_sql(str(default))
        upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {safe_default}"
        rollback = f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"
    else:
        upgrade = f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT"
        rollback = f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {_missing_def_placeholder(backend)}"
    return upgrade, rollback


def _build_mysql_alter_default_sql(
    table: str,
    column: str,
    default: Any,
    col_type: str | None = None,
    nullable: bool | None = None,
    my_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Emit MySQL-compatible MODIFY COLUMN for default changes.

    Uses MODIFY COLUMN with full column definition instead of
    ALTER COLUMN SET DEFAULT, which is more broadly compatible
    across MySQL versions including 5.7.
    """
    if col_type:
        _assert_complete_mysql_type(col_type)
    if default is not None:
        safe_default = _quote_default_for_sql(str(default))
        if not col_type:
            placeholder = _missing_def_placeholder(backend="mysql")
            upgrade = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {safe_default} {placeholder}"
            rollback = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT {placeholder}"
            return upgrade, rollback
        upgrade_def = _mysql_column_definition_for_meta(
            col_type, my_meta or {},
            nullable=nullable, default=safe_default,
        )
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {upgrade_def}"
        rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {_missing_def_placeholder(backend='mysql')}"
    else:
        if not col_type:
            placeholder = _missing_def_placeholder(backend="mysql")
            upgrade = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT {placeholder}"
            rollback = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {placeholder}"
            return upgrade, rollback
        upgrade_def = _mysql_column_definition_for_meta(
            col_type, my_meta or {}, nullable=nullable, default=None,
        )
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {upgrade_def}"
        rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {_missing_def_placeholder(backend='mysql')}"
    return upgrade, rollback


def _quote_default_for_sql(default: str) -> str:
    """Quote a default value for safe embedding in ALTER TABLE SQL.

    Numeric literals, SQL keywords, and function calls are left unquoted.
    String literals are wrapped in single quotes with proper escaping.
    """
    stripped = default.strip()
    if not stripped:
        return "NULL"
    if re.match(r"^-?\d+(\.\d+)?$", stripped):
        return stripped
    if re.match(r"^[A-Z_][A-Z0-9_]*$", stripped):
        return stripped
    if re.match(r"^\w+\(.*\)$", stripped):
        return stripped
    escaped = stripped.replace("'", "''")
    return f"'{escaped}'"


def _missing_def_placeholder(backend: str) -> str:
    """Return a hard-failure placeholder when column definition info is missing.

    Previously used ??? or <original_type>/<original_default> which produced
    misleading executable-looking SQL. Now emits an explicit SQL comment
    that will cause a controlled failure if executed.
    """
    if backend == "mysql":
        return "/* REQUIRES MANUAL COLUMN DEFINITION - type info unavailable */"
    return "<original_def_unavailable>"


_INCOMPLETE_MYSQL_TYPES = re.compile(
    r"^(VARCHAR|CHAR|VARBINARY|BINARY|ENUM|SET)$",
    re.IGNORECASE,
)


def _assert_complete_mysql_type(col_type: str) -> None:
    """Raise ValueError if a MySQL column type is incomplete (e.g. bare VARCHAR).

    MySQL requires length/values for VARCHAR, CHAR, VARBINARY, BINARY, ENUM, SET.
    Bare VARCHAR without a length parameter is invalid MySQL.
    """
    stripped = col_type.strip()
    if _INCOMPLETE_MYSQL_TYPES.match(stripped):
        raise ValueError(
            f"Incomplete MySQL column type '{col_type}' - "
            f"{stripped} requires a length or value list (e.g. {stripped}(255)). "
            f"Check the model column definition."
        )


def _build_pg_meta_sql(
    table: str,
    column: str,
    col_type: str,
    snap_type: str,
    to_pg_column: dict[str, Any],
    from_pg_column: dict[str, Any],
    backend: str,
) -> list[MigrationStatement]:
    if backend != "postgresql":
        return []

    mapping = [
        ("collation", "pg_collation"),
        ("storage", "pg_storage"),
        ("compression", "pg_compression"),
        ("generated", "pg_generated"),
        ("identity", "pg_identity"),
        ("identity_start", "pg_identity_start"),
        ("identity_increment", "pg_identity_increment"),
        ("identity_min", "pg_identity_min"),
        ("identity_max", "pg_identity_max"),
    ]
    stmts: list[MigrationStatement] = []
    for key, model_key in mapping:
        from_val = from_pg_column.get(key)
        to_val = to_pg_column.get(model_key)
        if from_val == to_val:
            continue
        if key == "collation":
            up = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {col_type} COLLATE \"{to_val}\";" if to_val else f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {col_type};"
            rb = f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {snap_type} COLLATE \"{from_val}\";" if from_val else f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {snap_type};"
        elif key == "storage":
            up = f"ALTER TABLE {table} ALTER COLUMN {column} SET STORAGE {to_val};" if to_val else f"ALTER TABLE {table} ALTER COLUMN {column} SET STORAGE EXTENDED;"
            rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET STORAGE {from_val};" if from_val else f"ALTER TABLE {table} ALTER COLUMN {column} SET STORAGE EXTENDED;"
        elif key == "compression":
            if to_val:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} SET COMPRESSION {to_val};"
            else:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} SET COMPRESSION DEFAULT;"
            if from_val:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET COMPRESSION {from_val};"
            else:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET COMPRESSION DEFAULT;"
        elif key == "generated":
            if to_val:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} SET EXPRESSION AS ({to_val});"
            else:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} DROP EXPRESSION;"
            if from_val:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET EXPRESSION AS ({from_val});"
            else:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} DROP EXPRESSION;"
        elif key == "identity":
            if to_val:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} ADD GENERATED {to_val} AS IDENTITY;"
            else:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} DROP IDENTITY IF EXISTS;"
            if from_val:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} ADD GENERATED {from_val} AS IDENTITY;"
            else:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} DROP IDENTITY IF EXISTS;"
        elif key in ("identity_start", "identity_increment", "identity_min", "identity_max"):
            pg_key = key.replace("identity_", "")
            if to_val is not None:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} SET ({pg_key} {to_val});"
            else:
                up = f"ALTER TABLE {table} ALTER COLUMN {column} SET ({pg_key} DEFAULT);"
            if from_val is not None:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET ({pg_key} {from_val});"
            else:
                rb = f"ALTER TABLE {table} ALTER COLUMN {column} SET ({pg_key} DEFAULT);"
        else:
            continue
        stmts.append(MigrationStatement(
            order=StatementOrder.ALTER_COLUMN_TYPE,
            upgrade_sql=up, rollback_sql=rb,
        ))
    return stmts


def _is_autoincrement(column: dict[str, Any]) -> bool:
    type_str = str(column.get("type", "")).lower()
    if any(kw in type_str for kw in ("serial", "bigserial", "smallserial")):
        return True
    if column.get("autoincrement"):
        return True
    default = column.get("default")
    if isinstance(default, str) and "nextval" in default.lower():
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

    if database_type is None:
        try:
            from dbwarden.config import get_database
            database_type = get_database(database).database_type
        except Exception:
            pass

    if database is None:
        try:
            from dbwarden.config import get_multi_db_config
            db_name = get_multi_db_config().default
        except Exception:
            db_name = "default"
    else:
        db_name = database

    if database_type == "clickhouse":
        if sqlalchemy_url is not None:
            from sqlalchemy import create_engine

            engine = create_engine(sqlalchemy_url)
            try:
                with engine.connect() as connection:
                    return _extract_clickhouse_schema_snapshot(connection, db_name)
            finally:
                engine.dispose()

        from dbwarden.database.connection import get_db_connection

        conn_context = get_db_connection(database)
        connection = conn_context.__enter__()
        try:
            return _extract_clickhouse_schema_snapshot(connection, db_name)
        finally:
            conn_context.__exit__(None, None, None)

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

            # For MySQL/MariaDB ENUM, store the full type with values
            if hasattr(col_type, "enums") and col_type.enums:
                enum_values = ", ".join(repr(v) for v in col_type.enums)
                col_entry["type"] = f"enum({enum_values})"

            comment = col.get("comment")
            if comment is not None:
                col_entry["comment"] = comment

            if database_type == "postgresql":
                # Enum detection: check SQLAlchemy type object directly
                if hasattr(col_type, "enums") and col_type.enums and hasattr(col_type, "name") and col_type.name:
                    col_entry["type"] = "enum"
                    col_entry["enum_name"] = col_type.name
                    col_entry["pg_type"] = {
                        "kind": "enum",
                        "type_name": col_type.name,
                        "values": list(col_type.enums),
                    }
                # Fallback: raw type string might be the enum type name
                enum_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)$", raw_type_str)
                if enum_match and engine is not None:
                    try:
                        with engine.connect() as conn:
                            enum_row = conn.execute(
                                text("SELECT t.oid, t.typname FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = :tname LIMIT 1"),
                                {"tname": raw_type_str},
                            ).fetchone()
                            if enum_row:
                                col_entry["type"] = "enum"
                                col_entry["enum_name"] = raw_type_str
                                val_rows = conn.execute(
                                    text("SELECT enumlabel FROM pg_enum WHERE enumtypid = :oid ORDER BY enumsortorder"),
                                    {"oid": enum_row[0]},
                                ).fetchall()
                                col_entry["pg_type"] = {
                                    "kind": "enum",
                                    "type_name": raw_type_str,
                                    "values": [r[0] for r in val_rows],
                                }
                    except Exception:
                        pass

                pg_column: dict[str, Any] = {}
                if col.get("identity"):
                    identity = col["identity"]
                    pg_column["identity"] = "always" if identity.get("always") else "by_default"
                    if identity.get("start") is not None:
                        pg_column["identity_start"] = identity["start"]
                    if identity.get("increment") is not None:
                        pg_column["identity_increment"] = identity["increment"]
                    if identity.get("minvalue") is not None:
                        pg_column["identity_min"] = identity["minvalue"]
                    if identity.get("maxvalue") is not None:
                        pg_column["identity_max"] = identity["maxvalue"]
                type_obj = col["type"]
                collation = getattr(type_obj, "collation", None)
                if collation:
                    pg_column["collation"] = collation
                if col.get("computed"):
                    pg_column["generated"] = col["computed"].get("sqltext", "")

                # pg_type for specialized types
                type_str_lower = raw_type_str.lower()
                if getattr(type_obj, "item_type", None) is not None:
                    col_entry["pg_type"] = {"kind": "array", "inner": str(type_obj.item_type), "dimensions": 1}
                    col_entry["type"] = "array"
                elif type_str_lower in ("tsvector",):
                    regconfig = getattr(type_obj, "regconfig", None)
                    pg_type_entry: dict[str, Any] = {"kind": "tsvector"}
                    if regconfig:
                        pg_type_entry["config"] = str(regconfig)
                    col_entry["pg_type"] = pg_type_entry
                    col_entry["type"] = "tsvector"
                elif type_str_lower == "jsonb":
                    col_entry["pg_type"] = {"kind": "jsonb"}
                elif normalized.get("has_timezone") and col_entry.get("type") == "timestamp":
                    col_entry["pg_type"] = {"kind": "timestamptz"}
                elif col_entry.get("enum_name"):
                    pass  # pg_type already set above
                else:
                    try:
                        if engine is not None:
                            with engine.connect() as _c:
                                range_row = _c.execute(
                                    text("SELECT rngtypid::regtype::text FROM pg_range WHERE rngtypid = (SELECT oid FROM pg_type WHERE typname = :t)"),
                                    {"t": raw_type_str.lower()},
                                ).fetchone()
                                if range_row:
                                    col_entry["pg_type"] = {"kind": "range", "range_type": raw_type_str}
                                    col_entry["type"] = raw_type_str
                    except Exception:
                        pass

                if pg_column:
                    col_entry["pg_column"] = pg_column

            if database_type in ("mysql", "mariadb"):
                my_column: dict[str, Any] = {}
                type_obj = col.get("type")
                charset = getattr(type_obj, "charset", None)
                collation = getattr(type_obj, "collation", None)
                unsigned = bool(getattr(type_obj, "unsigned", False))
                if charset:
                    my_column["my_charset"] = charset
                if collation:
                    my_column["my_collate"] = collation
                if unsigned:
                    my_column["my_unsigned"] = True
                if my_column:
                    col_entry["my_column"] = my_column

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

            _conn = engine.connect() if own_engine and engine is not None else connection
            try:
                pg_table: dict[str, Any] = {}

                try:
                    rows = _conn.execute(
                        text("SELECT unnest(COALESCE(reloptions, '{}')) FROM pg_class WHERE relname = :t"),
                        {"t": table_name},
                    ).fetchall()
                    params: dict[str, Any] = {}
                    for row in rows:
                        kv = row[0].split("=", 1)
                        if len(kv) == 2:
                            key = f"pg_{kv[0]}"
                            val: Any = kv[1]
                            if val.isdigit():
                                val = int(val)
                            params[key] = val
                    if params:
                        pg_table.update(params)
                except Exception:
                    pass

                try:
                    row = _conn.execute(
                        text("SELECT relpersistence FROM pg_class WHERE relname = :t"),
                        {"t": table_name},
                    ).fetchone()
                    if row and row[0] == 'u':
                        pg_table["pg_unlogged"] = True
                except Exception:
                    pass

                try:
                    row = _conn.execute(
                        text(
                            "SELECT spcname FROM pg_tablespace t "
                            "JOIN pg_class c ON c.reltablespace = t.oid "
                            "WHERE c.relname = :t"
                        ),
                        {"t": table_name},
                    ).fetchone()
                    if row:
                        pg_table["pg_tablespace"] = row[0]
                except Exception:
                    pass

                try:
                    rows = _conn.execute(
                        text("SELECT inhparent::regclass::text FROM pg_inherits WHERE inhrelid = CAST(:t AS regclass)"),
                        {"t": table_name},
                    ).fetchall()
                    parents = [r[0] for r in rows]
                    if len(parents) == 1:
                        pg_table["pg_inherits"] = parents[0]
                    elif parents:
                        pg_table["pg_inherits"] = parents
                except Exception:
                    pass

                try:
                    part_row = _conn.execute(
                        text(
                            "SELECT p.partstrat, "
                            "array_agg(a.attname ORDER BY a.attnum) AS part_columns, "
                            "pg_get_expr(p.partexprs, p.partrelid) AS part_expr "
                            "FROM pg_partitioned_table p "
                            "JOIN pg_class c ON c.oid = p.partrelid "
                            "LEFT JOIN pg_attribute a ON a.attrelid = p.partrelid AND a.attnum = ANY(p.partattrs) "
                            "WHERE c.relname = :t "
                            "GROUP BY p.partstrat, p.partexprs, p.partrelid"
                        ),
                        {"t": table_name},
                    ).fetchone()
                    if part_row:
                        strat_map = {"r": "RANGE", "l": "LIST", "h": "HASH"}
                        strategy = strat_map.get(part_row[0], part_row[0])
                        part_columns = list(part_row[1] or [])
                        part_expr = part_row[2]
                        if part_expr:
                            part_columns.append(part_expr.strip())
                        pg_table["pg_partition"] = {
                            "strategy": strategy,
                            "columns": part_columns,
                        }
                except Exception:
                    pass

                try:
                    rows = _conn.execute(
                        text(
                            "SELECT conname, pg_get_constraintdef(oid) AS definition " 
                            "FROM pg_constraint "
                            "WHERE conrelid = CAST(:t AS regclass) AND contype = 'x'"
                        ),
                        {"t": table_name},
                    ).fetchall()
                    excludes = [{"name": r[0], "expression": r[1]} for r in rows]
                    if excludes:
                        pg_table["pg_excludes"] = excludes
                except Exception:
                    pass

                try:
                    rows = _conn.execute(
                        text(
                            "SELECT a.attname, a.attstorage, a.attcompression "
                            "FROM pg_attribute a "
                            "WHERE a.attrelid = CAST(:t AS regclass) AND a.attnum > 0 AND NOT a.attisdropped "
                            "ORDER BY a.attnum"
                        ),
                        {"t": table_name},
                    ).fetchall()
                    storage_map = {'p': 'PLAIN', 'm': 'MAIN', 'e': 'EXTERNAL', 'x': 'EXTENDED'}
                    for r in rows:
                        cname = r[0]
                        if cname in columns_dict:
                            pg_col = columns_dict[cname].get("pg_column", {})
                            if isinstance(pg_col, dict):
                                if r[1]:
                                    pg_col["storage"] = storage_map.get(r[1], r[1])
                                if r[2]:
                                    pg_col["compression"] = r[2]
                                if pg_col:
                                    columns_dict[cname]["pg_column"] = pg_col
                except Exception:
                    pass

                if pg_table:
                    table_entry["pg_table"] = pg_table
            except Exception:
                pass
            finally:
                if own_engine and _conn is not None:
                    try:
                        _conn.close()
                    except Exception:
                        pass

        if database_type in ("mysql", "mariadb"):
            _conn = engine.connect() if own_engine and engine is not None else connection
            try:
                my_table: dict[str, Any] = {}

                try:
                    row = _conn.execute(
                        text(
                            "SELECT ENGINE, TABLE_COLLATION, AUTO_INCREMENT, ROW_FORMAT, TABLE_COMMENT "
                            "FROM information_schema.TABLES "
                            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                        ),
                        {"t": table_name},
                    ).fetchone()
                    if row:
                        if row[0]:
                            my_table["my_engine"] = row[0]
                        if row[1]:
                            my_table["my_collate"] = row[1]
                            charset = str(row[1]).split("_", 1)[0]
                            if charset:
                                my_table["my_charset"] = charset
                        if row[2] is not None:
                            my_table["my_auto_increment"] = int(row[2])
                        if row[3]:
                            my_table["my_row_format"] = row[3]
                        if row[4]:
                            table_entry["comment"] = row[4]
                except Exception:
                    pass

                try:
                    rows = _conn.execute(
                        text(
                            "SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_SET_NAME, COLLATION_NAME, EXTRA, COLUMN_COMMENT "
                            "FROM information_schema.COLUMNS "
                            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                        ),
                        {"t": table_name},
                    ).fetchall()
                    for row in rows:
                        col_entry = columns_dict.get(row[0])
                        if col_entry is None:
                            continue
                        my_column = dict(col_entry.get("my_column", {}) or {})
                        column_type = str(row[1] or "")
                        if "unsigned" in column_type.lower():
                            my_column["my_unsigned"] = True
                        if row[2]:
                            my_column["my_charset"] = row[2]
                        if row[3]:
                            my_column["my_collate"] = row[3]
                        extra = str(row[4] or "")
                        if "auto_increment" in extra.lower():
                            col_entry["autoincrement"] = True
                        on_update_match = re.search(r"on update\s+(.+)$", extra, re.IGNORECASE)
                        if on_update_match:
                            my_column["my_on_update"] = on_update_match.group(1).strip()
                        if row[5]:
                            col_entry["comment"] = row[5]
                        if my_column:
                            col_entry["my_column"] = my_column
                except Exception:
                    pass

                if my_table:
                    table_entry["my_table"] = my_table
            except Exception:
                pass
            finally:
                if own_engine and _conn is not None:
                    try:
                        _conn.close()
                    except Exception:
                        pass

        tables[table_name] = table_entry

        for idx in inspector.get_indexes(table_name):
            idx_name = idx.get("name", "")
            if not idx_name:
                continue
            if idx.get("unique") and set(idx.get("column_names", [])) == pk_columns:
                continue
            idx_entry: dict[str, Any] = {
                "table": table_name,
                "name": idx_name,
                "columns": list(idx.get("column_names", [])),
                "unique": bool(idx.get("unique", False)),
            }
            idx_dialect = idx.get("dialect_options", {})
            for k in ("postgresql_using", "mysql_using", "mariadb_using", "sqlite_using"):
                val = idx_dialect.get(k)
                if val:
                    idx_entry["using"] = val
                    break
            if "using" not in idx_entry:
                idx_entry["using"] = "btree"
            for k in ("postgresql_where",):
                val = idx_dialect.get(k)
                if val:
                    idx_entry["where"] = val
                    break
            incl = idx.get("include_columns")
            if incl:
                idx_entry["include"] = list(incl)
            for k in ("postgresql_with",):
                val = idx_dialect.get(k)
                if val:
                    idx_entry["with_params"] = val
                    break
            for k in ("postgresql_tablespace",):
                val = idx_dialect.get(k)
                if val:
                    idx_entry["tablespace"] = val
                    break
            for k in ("postgresql_nulls_not_distinct",):
                val = idx_dialect.get(k)
                if val:
                    idx_entry["nulls_not_distinct"] = True
                    break

            if database_type == "postgresql" and idx_name and engine is not None:
                try:
                    with engine.connect() as _c:
                        sort_rows = _c.execute(
                            text("""
                                SELECT a.attname,
                                       pg_index_column_has_property(i.indexrelid, k, 'asc') AS is_asc,
                                       pg_index_column_has_property(i.indexrelid, k, 'nulls_first') AS nf
                                FROM pg_index i
                                CROSS JOIN LATERAL generate_series(1, array_length(i.indkey, 1)) AS k
                                JOIN pg_class ci ON ci.oid = i.indexrelid
                                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[k]
                                WHERE ci.relname = :idxname AND i.indkey[k] <> 0
                                ORDER BY k
                            """),
                            {"idxname": idx_name},
                        ).fetchall()
                        sorting: dict[str, str] = {}
                        for r in sort_rows:
                            parts: list[str] = []
                            if r.is_asc is False:
                                parts.append("DESC")
                            if r.nf is False:
                                parts.append("NULLS LAST")
                            elif r.nf is True:
                                parts.append("NULLS FIRST")
                            if parts:
                                sorting[r.attname] = " ".join(parts)
                        if sorting:
                            idx_entry["column_sorting"] = sorting
                except Exception:
                    pass
            indexes[f"{table_name}.{idx_name}"] = idx_entry

        for fk in inspector.get_foreign_keys(table_name):
            fk_name = fk.get("name", "")
            if not fk_name:
                fk_name = f"fk_{table_name}_{'_'.join(fk.get('constrained_columns', []))}"
            fk_options = fk.get("options", {})
            constraints[f"{table_name}.{fk_name}"] = {
                "type": "foreign_key",
                "name": fk_name,
                "table": table_name,
                "columns": list(fk.get("constrained_columns", [])),
                "referenced_table": fk.get("referred_table", ""),
                "referenced_columns": list(fk.get("referred_columns", [])),
                "on_delete": fk_options.get("ondelete", "NO ACTION"),
                "on_update": fk_options.get("onupdate", "NO ACTION"),
                "deferrable": bool(fk_options.get("deferrable", False)),
            }

        for uq in inspector.get_unique_constraints(table_name):
            uq_name = uq.get("name", "")
            if not uq_name:
                continue
            constraints[f"{table_name}.{uq_name}"] = {
                "type": "unique",
                "name": uq_name,
                "table": table_name,
                "columns": list(uq.get("column_names", [])),
            }

        for ck in inspector.get_check_constraints(table_name):
            ck_name = ck.get("name", "")
            if not ck_name:
                ck_name = f"ck_{table_name}_{hash(ck.get('sqltext', ''))}"
            constraints[f"{table_name}.{ck_name}"] = {
                "type": "check",
                "name": ck_name,
                "table": table_name,
                "columns": [],
                "expression": ck.get("sqltext", ""),
            }

        if database_type == "postgresql":
            _pg_conn = engine.connect() if own_engine else connection
            try:
                no_inherit_rows = _pg_conn.execute(
                    text("SELECT conname, connoinherit FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'c'"),
                    {"t": table_name},
                ).fetchall()
                for r in no_inherit_rows:
                    if r[1]:
                        cname = f"{table_name}.{r[0]}"
                        if cname in constraints:
                            constraints[cname]["no_inherit"] = True
            except Exception:
                pass
            try:
                defer_rows = _pg_conn.execute(
                    text("SELECT conname, condeferrable, condeferred FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'u'"),
                    {"t": table_name},
                ).fetchall()
                for r in defer_rows:
                    cname = f"{table_name}.{r[0]}"
                    if cname in constraints:
                        constraints[cname]["deferrable"] = bool(r[1])
                        constraints[cname]["initially_deferred"] = bool(r[2])
            except Exception:
                pass
            if own_engine:
                _pg_conn.close()

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


def _extract_clickhouse_schema_snapshot(connection: Any, db_name: str) -> dict[str, Any]:
    from sqlalchemy import text
    from dbwarden.databases.clickhouse.engine import ChEngineSpec

    tables: dict[str, Any] = {}
    enums: dict[str, Any] = {}
    indexes: dict[str, Any] = {}
    constraints: dict[str, Any] = {}

    table_rows = connection.execute(
        text(
            "SELECT name, engine, engine_full, sorting_key, primary_key, partition_key, "
            "sampling_key, create_table_query, comment "
            "FROM system.tables WHERE database = currentDatabase()"
        )
    ).fetchall()

    column_rows = connection.execute(
        text(
            "SELECT table, name, type, default_kind, default_expression, compression_codec AS codec_expression, "
            "NULL AS ttl_expression, comment, is_in_primary_key, is_in_sorting_key, is_in_partition_key "
            "FROM system.columns WHERE database = currentDatabase()"
        )
    ).fetchall()

    index_rows = connection.execute(
        text(
            "SELECT table, name, type, expr, granularity FROM system.data_skipping_indices "
            "WHERE database = currentDatabase()"
        )
    ).fetchall()

    columns_by_table: dict[str, list[dict[str, Any]]] = {}
    for row in column_rows:
        columns_by_table.setdefault(row.table, []).append({
            "name": row.name,
            "type": row.type,
            "default_kind": getattr(row, "default_kind", None),
            "default_expression": getattr(row, "default_expression", None),
            "codec_expression": getattr(row, "codec_expression", None),
            "ttl_expression": getattr(row, "ttl_expression", None),
            "comment": getattr(row, "comment", None),
            "is_in_primary_key": bool(getattr(row, "is_in_primary_key", False)),
            "is_in_sorting_key": bool(getattr(row, "is_in_sorting_key", False)),
            "is_in_partition_key": bool(getattr(row, "is_in_partition_key", False)),
        })

    indexes_by_table: dict[str, list[dict[str, Any]]] = {}
    for row in index_rows:
        indexes_by_table.setdefault(row.table, []).append({
            "name": row.name,
            "type": row.type,
            "expr": row.expr,
            "granularity": row.granularity,
        })

    for row in table_rows:
        table_name = row.name
        create_query = getattr(row, "create_table_query", "") or ""
        engine_name = getattr(row, "engine", "") or ""
        engine_full = getattr(row, "engine_full", "") or ""
        comment = getattr(row, "comment", None) or None

        if engine_name.upper() == "DICTIONARY":
            object_type = "dictionary"
        elif create_query.strip().upper().startswith("CREATE MATERIALIZED VIEW"):
            object_type = "materialized_view"
        else:
            object_type = "table"

        ch_engine = ChEngineSpec.from_engine_string(engine_full or engine_name)
        ch_engine_serialized = _serialize_clickhouse_engine(ch_engine)

        sorting_key = _clickhouse_tuple_or_list(getattr(row, "sorting_key", None))
        primary_key = _clickhouse_tuple_or_list(getattr(row, "primary_key", None))
        partition_key = _clean_clickhouse_expression(getattr(row, "partition_key", None))
        sampling_key = _clean_clickhouse_expression(getattr(row, "sampling_key", None))

        ch_options: dict[str, Any] = {
            "ch_engine_raw": ch_engine.to_dict(),
            "ch_engine": ch_engine_serialized,
            "ch_order_by": sorting_key,
            "ch_primary_key": primary_key,
            "ch_partition_by": partition_key,
            "ch_sample_by": sampling_key,
            "ch_ttl": _parse_clickhouse_ttl_expressions(create_query),
            "ch_settings": _parse_clickhouse_settings(create_query),
            "ch_object_type": object_type,
            "ch_select_statement": _parse_clickhouse_mv_query(create_query),
            "ch_to_table": _parse_clickhouse_mv_to_table(create_query),
            "ch_dictionary": object_type == "dictionary",
            "ch_dict_layout": _parse_clickhouse_dict_layout(create_query),
            "ch_dict_source": _parse_clickhouse_dict_source(create_query),
            "ch_dict_lifetime": _parse_clickhouse_dict_lifetime(create_query),
            "ch_dict_primary_key": _parse_clickhouse_dict_primary_key(create_query),
            "ch_projections": _parse_clickhouse_projection_queries(create_query),
            "ch_zookeeper_path": _parse_clickhouse_zookeeper_path(create_query, engine_name),
            "ch_replica_name": _parse_clickhouse_replica_name(create_query, engine_name),
        }

        columns_dict: dict[str, Any] = {}
        for col in columns_by_table.get(table_name, []):
            raw_type = col["type"]
            ch_nullable = str(raw_type).startswith("Nullable(")
            ch_low_cardinality = "LowCardinality(" in str(raw_type)
            default_kind = col.get("default_kind")
            default_expression = col.get("default_expression")
            ch_column: dict[str, Any] = {
                "ch_codec": _pick_clickhouse_codec(col.get("codec_expression")),
                "ch_default_expression": default_expression if default_kind == "DEFAULT" else None,
                "ch_materialized": default_expression if default_kind == "MATERIALIZED" else None,
                "ch_alias": default_expression if default_kind == "ALIAS" else None,
                "ch_ttl": col.get("ttl_expression"),
                "ch_low_cardinality": ch_low_cardinality,
                "ch_nullable": ch_nullable,
                "ch_type": raw_type,
            }

            columns_dict[col["name"]] = {
                "type": raw_type,
                "nullable": ch_nullable,
                "primary_key": bool(col.get("is_in_primary_key", False)),
                "default": default_expression if default_kind == "DEFAULT" else None,
                "comment": col.get("comment"),
                "ch_column": ch_column,
            }

        table_entry: dict[str, Any] = {
            "object_type": object_type,
            "columns": columns_dict,
            "primary_key": [c for c in (primary_key or [])] if isinstance(primary_key, list) else ([primary_key] if isinstance(primary_key, str) and primary_key else []),
            "comment": comment,
            "indexes": indexes_by_table.get(table_name, []),
            "ch_options": ch_options,
            "clickhouse_options": ch_options,
        }
        tables[table_name] = table_entry

    return {
        "format_version": 1,
        "migration_id": "",
        "database_name": db_name,
        "database_type": "clickhouse",
        "applied_at": "",
        "tables": tables,
        "enums": enums,
        "indexes": indexes,
        "constraints": constraints,
    }


def _serialize_clickhouse_engine(engine: Any) -> str | tuple | None:
    if engine is None:
        return None
    if isinstance(engine, dict):
        name = engine.get("name")
        if not name:
            return None
        args = list(engine.get("args", []) or [])
        if engine.get("zookeeper_path") is not None:
            args.insert(0, engine["zookeeper_path"])
        if engine.get("replica_name") is not None:
            args.insert(1 if engine.get("zookeeper_path") is not None else 0, engine["replica_name"])
        if not args:
            return name
        return tuple([name] + args)
    if hasattr(engine, "name"):
        args = [engine.name]
        if getattr(engine, "zookeeper_path", None) is not None:
            args.append(engine.zookeeper_path)
        if getattr(engine, "replica_name", None) is not None:
            args.append(engine.replica_name)
        args.extend(list(getattr(engine, "args", ()) or ()))
        return args[0] if len(args) == 1 else tuple(args)
    return engine


def _clickhouse_tuple_or_list(value: Any) -> str | list[str] | None:
    if value is None:
        return None
    value_str = str(value).strip()
    if not value_str:
        return None
    if value_str.startswith("tuple(") and value_str.endswith(")"):
        inner = value_str[6:-1].strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",")]
    return value_str


def _clean_clickhouse_expression(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


def _parse_clickhouse_ttl_expressions(create_query: str) -> list[str]:
    ttl_match = re.search(
        r"\bTTL\s+(.+?)(?:\n(?:SETTINGS|COMMENT|AS|PRIMARY KEY|ORDER BY|PARTITION BY|SAMPLE BY)\b|$)",
        create_query,
        re.IGNORECASE | re.DOTALL,
    )
    if not ttl_match:
        return []
    ttl_body = ttl_match.group(1).strip()
    return [part.strip() for part in ttl_body.split(",") if part.strip()]


def _parse_clickhouse_projection_queries(create_query: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    pattern = re.compile(r"PROJECTION\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.IGNORECASE)
    pos = 0
    while True:
        match = pattern.search(create_query, pos)
        if not match:
            break
        name = match.group(1)
        query = _extract_balanced_parens(match)
        results.append({"name": name, "query": (query or "").strip()})
        pos = match.end()
    return results


def _parse_clickhouse_projection_names(create_query: str) -> list[str]:
    return [p["name"] for p in _parse_clickhouse_projection_queries(create_query)]


def _parse_clickhouse_mv_query(create_query: str) -> str | None:
    mv_match = re.search(r"\bAS\s+SELECT\s+.+$", create_query, re.IGNORECASE | re.DOTALL)
    if not mv_match:
        return None
    return mv_match.group(0)[3:].strip()


def _parse_clickhouse_mv_to_table(create_query: str) -> str | None:
    match = re.search(r"\bTO\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", create_query, re.IGNORECASE)
    return match.group(1) if match else None


def _parse_clickhouse_zookeeper_path(create_query: str, engine: str) -> str | None:
    if "Replicated" not in engine:
        return None
    match = re.search(r"\bReplicated\w+\s*\(([^,]+),", create_query)
    if match:
        return match.group(1).strip()
    return None


def _parse_clickhouse_replica_name(create_query: str, engine: str) -> str | None:
    if "Replicated" not in engine:
        return None
    match = re.search(r"\bReplicated\w+\s*\([^,]+,\s*([^\)]+)\)", create_query)
    if match:
        return match.group(1).strip()
    return None


def _parse_clickhouse_settings(create_query: str) -> dict[str, str] | None:
    settings_match = re.search(r"\bSETTINGS\s+(.+?)(?:\s+(?:COMMENT|AS)\b|$)", create_query, re.IGNORECASE)
    if not settings_match:
        return None
    settings: dict[str, str] = {}
    for item in settings_match.group(1).split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        settings[key.strip()] = value.strip().strip("'\"")
    return settings or None


def _extract_balanced_parens(match: re.Match) -> str | None:
    """Extract content between the first balanced outer parens."""
    start = match.end() - 1  # position of opening paren
    depth = 0
    for i in range(start, len(match.string)):
        ch = match.string[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return match.string[start + 1 : i]
    return None


def _parse_clickhouse_dict_layout(create_query: str) -> str | None:
    match = re.search(r"\bLAYOUT\s*\(", create_query, re.IGNORECASE)
    return _extract_balanced_parens(match) if match else None


def _parse_clickhouse_dict_source(create_query: str) -> str | None:
    match = re.search(r"\bSOURCE\s*\(", create_query, re.IGNORECASE)
    return _extract_balanced_parens(match) if match else None


def _parse_clickhouse_dict_lifetime(create_query: str) -> str | int | None:
    match = re.search(r"\bLIFETIME\s*\(", create_query, re.IGNORECASE)
    if not match:
        return None
    value = _extract_balanced_parens(match)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def _parse_clickhouse_dict_primary_key(create_query: str) -> str | None:
    match = re.search(r"\bPRIMARY\s+KEY\s+(.+?)(?=\s+(?:SOURCE|LAYOUT|LIFETIME)\b)", create_query, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _pick_clickhouse_codec(codec_expr: Any) -> str | None:
    if codec_expr is None:
        return None
    codec = str(codec_expr).strip()
    if not codec:
        return None
    parts = [part.strip() for part in codec.split(",") if part.strip()]
    if not parts:
        return None
    non_default = [part for part in parts if not part.upper().startswith("LZ4")]
    return non_default[-1] if non_default else parts[-1]


def compute_checksum(snapshot: dict[str, Any]) -> str:
    snapshot_copy = {k: v for k, v in snapshot.items() if k != "checksum"}
    raw = json.dumps(snapshot_copy, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_schemas_directory(database: str | None = None) -> str:
    base_dir = os.path.join(os.getcwd(), ".dbwarden", "schemas")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def write_snapshot(
    snapshot: dict[str, Any],
    database: str | None = None,
    migration_id: str = "",
) -> str:
    from dbwarden.config import get_database
    from sqlalchemy.engine import make_url

    config = get_database(database)
    if database:
        db_name = database
    else:
        parsed = make_url(config.sqlalchemy_url)
        db_name = parsed.database or "default"

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
            import logging
            logging.getLogger("dbwarden.snapshot").warning(
                "Snapshot checksum mismatch for %s (expected %s, got %s)",
                filepath, stored_checksum, actual,
            )
            return None
    else:
        snapshot["checksum"] = ""

    return snapshot


def find_latest_snapshot(database: str | None = None) -> dict[str, Any] | None:
    schemas_dir = get_schemas_directory(database)

    if not os.path.isdir(schemas_dir):
        return None

    if database is None:
        try:
            from dbwarden.config import get_multi_db_config
            db_name = get_multi_db_config().default
        except Exception:
            db_name = "default"
    else:
        db_name = database

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


def _compute_table_overlap(
    dropped_table: str,
    added_table: str,
    snapshot: dict[str, Any],
    model_tables: list[ModelTable],
) -> float:
    snap_cols = snapshot["tables"][dropped_table]["columns"]
    model_table = next((t for t in model_tables if t.name == added_table), None)
    if model_table is None:
        return 0.0

    model_cols = {
        col.name.lower(): normalize_type(col.type)["type"]
        for col in model_table.columns
    }
    snap_cols_normalized = {
        name: col.get("type", "")
        for name, col in snap_cols.items()
    }

    matches = sum(
        1 for name, typ in model_cols.items()
        if snap_cols_normalized.get(name) == typ
    )
    max_cols = max(len(model_cols), len(snap_cols_normalized))
    return matches / max_cols if max_cols > 0 else 0.0


RENAME_TABLE_OVERLAP_THRESHOLD = 0.6


def _build_ch_projection_sql(
    table: str,
    to_val: Any,
    from_val: Any,
    up_stmts: list[str],
    rb_stmts: list[str],
) -> None:
    snap_projs: list[dict] = from_val or []
    model_projs: list[dict] = to_val or []
    snap_by_name = {p.get("name"): p for p in snap_projs}
    model_by_name = {p.get("name"): p for p in model_projs}
    for name, snap_p in snap_by_name.items():
        if name not in model_by_name:
            up_stmts.append(f"ALTER TABLE {table} DROP PROJECTION {name}")
            model_p = model_by_name.get(name)
            if model_p:
                rb_stmts.append(f"ALTER TABLE {table} ADD PROJECTION {name} {model_p.get('query', '')}")
            else:
                rb_stmts.append(f"ALTER TABLE {table} ADD PROJECTION {name} {snap_p.get('query', '')}")
    for name, model_p in model_by_name.items():
        if name not in snap_by_name:
            up_stmts.append(f"ALTER TABLE {table} ADD PROJECTION {name} {model_p.get('query', '')}")
            rb_stmts.append(f"ALTER TABLE {table} DROP PROJECTION {name}")
            continue
        snap_p = snap_by_name[name]
        if model_p.get("query") != snap_p.get("query"):
            up_stmts.append(f"ALTER TABLE {table} DROP PROJECTION {name}")
            up_stmts.append(f"ALTER TABLE {table} ADD PROJECTION {name} {model_p.get('query', '')}")
            rb_stmts.append(f"ALTER TABLE {table} DROP PROJECTION {snap_p.get('name', name)}")
            rb_stmts.append(f"ALTER TABLE {table} ADD PROJECTION {name} {snap_p.get('query', '')}")


def _rename_table_sql(intent: TableRenameIntent, backend: str) -> MigrationStatement:
    if backend == "clickhouse":
        return MigrationStatement(
            order=StatementOrder.RENAME_TABLE,
            upgrade_sql=f"RENAME TABLE {intent.old_table} TO {intent.new_table};",
            rollback_sql=f"RENAME TABLE {intent.new_table} TO {intent.old_table};",
        )

    upgrade = f"ALTER TABLE {intent.old_table} RENAME TO {intent.new_table};"
    rollback = f"ALTER TABLE {intent.new_table} RENAME TO {intent.old_table};"

    return MigrationStatement(
        order=StatementOrder.RENAME_TABLE,
        upgrade_sql=upgrade,
        rollback_sql=rollback,
    )


def _index_sig(idx_or_info: dict | IndexInfo) -> tuple:
    if isinstance(idx_or_info, IndexInfo):
        return (
            tuple(idx_or_info.columns),
            idx_or_info.unique,
            idx_or_info.using or "btree",
            idx_or_info.where,
            tuple(idx_or_info.include or []),
            tuple(sorted((idx_or_info.with_params or {}).items())),
            idx_or_info.tablespace,
            idx_or_info.nulls_not_distinct,
            tuple((idx_or_info.column_sorting or {}).items()),
            idx_or_info.clickhouse_type,
            idx_or_info.clickhouse_granularity,
        )
    return (
        tuple(idx_or_info.get("columns", [])),
        bool(idx_or_info.get("unique", False)),
        idx_or_info.get("using") or "btree",
        idx_or_info.get("where"),
        tuple(idx_or_info.get("include", []) or []),
        tuple(sorted((idx_or_info.get("with_params") or {}).items())),
        idx_or_info.get("tablespace"),
        bool(idx_or_info.get("nulls_not_distinct", False)),
        tuple(sorted((idx_or_info.get("column_sorting") or {}).items())),
        idx_or_info.get("clickhouse_type"),
        idx_or_info.get("clickhouse_granularity"),
    )


def _index_op_from_info(info: IndexInfo, table: str) -> dict[str, Any]:
    op: dict[str, Any] = {
        "type": "add_index",
        "table": table,
        "columns": info.columns,
        "unique": info.unique,
    }
    if info.using is not None:
        op["using"] = info.using
    if info.where is not None:
        op["where"] = info.where
    if info.include is not None:
        op["include"] = info.include
    if info.with_params is not None:
        op["with_params"] = info.with_params
    if info.tablespace is not None:
        op["tablespace"] = info.tablespace
    if info.nulls_not_distinct:
        op["nulls_not_distinct"] = True
    if info.column_sorting is not None:
        op["column_sorting"] = info.column_sorting
    if not info.concurrently:
        op["concurrently"] = False
    if info.clickhouse_type is not None:
        op["clickhouse_type"] = info.clickhouse_type
    if info.clickhouse_granularity is not None:
        op["clickhouse_granularity"] = info.clickhouse_granularity
    return op


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


def _check_ch_engine_recreate_allowed(snap_spec: dict, model_spec: dict, table_name: str) -> None:
    reasons: list[str] = []
    for spec, label in [(snap_spec, "current"), (model_spec, "new")]:
        if spec.get("ch_object_type") == "materialized_view" and spec.get("ch_to_table"):
            reasons.append(f"is a materialized view with 'TO {spec['ch_to_table']}' ({label})")
        elif spec.get("ch_select_statement") and spec.get("ch_to_table"):
            reasons.append(f"has a SELECT statement and 'TO' target ({label})")
    if reasons:
        raise ValueError(
            f"ClickHouse table '{table_name}' cannot be automatically recreated: "
            f"{'; '.join(reasons)}. "
            "Handle manually or use --force to skip this check."
        )


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


def _diff_ch_options(
    snap_opts: dict,
    model_opts: dict,
    table_name: str,
    upgrade_ops: list[dict],
    rollback_ops: list[dict],
    snapshot_table: dict[str, Any] | None = None,
    model_table: ModelTable | None = None,
    clickhouse_engine_recreate: bool = False,
) -> None:
    if snap_opts.get("ch_engine") != model_opts.get("ch_engine") and snap_opts.get("ch_engine") is not None and model_opts.get("ch_engine") is not None and snapshot_table is not None and model_table is not None:
        _check_ch_engine_recreate_allowed(snap_opts, model_opts, table_name)
        from dbwarden.engine.offline import _table_to_state_entry

        upgrade_ops.append({
            "type": "recreate_ch_table",
            "table": table_name,
            "reason": "ch_engine",
            "from_table": {
                "name": table_name,
                **snapshot_table,
                "backend_table_spec": {"backend": "clickhouse", **snap_opts},
            },
            "to_table": _table_to_state_entry(model_table),
            "drop_old_after_swap": False,
            "preserve_old_suffix": "__dbw_old",
            "failed_suffix": "__dbw_failed",
        })
        rollback_ops.append({
            "type": "recreate_ch_table",
            "table": table_name,
            "reason": "ch_engine",
            "from_table": _table_to_state_entry(model_table),
            "to_table": {
                "name": table_name,
                **snapshot_table,
                "backend_table_spec": {"backend": "clickhouse", **snap_opts},
            },
            "drop_old_after_swap": False,
            "preserve_old_suffix": "__dbw_failed",
            "failed_suffix": "__dbw_old",
        })
        return

    ch_changes: dict[str, dict[str, Any]] = {}
    for key in _CH_OPTION_KEYS:
        snap_val = snap_opts.get(key)
        model_val = model_opts.get(key)
        if json.dumps(snap_val, sort_keys=True, default=str) != json.dumps(model_val, sort_keys=True, default=str):
            if snap_val is None and model_val is None:
                continue
            ch_changes[key] = {"from": snap_val, "to": model_val}

    has_recreate_keys = any(k in _RECREATE_REQUIRED_CH_KEYS for k in ch_changes)
    if has_recreate_keys and clickhouse_engine_recreate and snapshot_table is not None and model_table is not None:
        from dbwarden.engine.offline import _table_to_state_entry

        reason = ",".join(k for k in ch_changes if k in _RECREATE_REQUIRED_CH_KEYS)
        upgrade_ops.append({
            "type": "recreate_ch_table",
            "table": table_name,
            "reason": reason,
            "from_table": {
                "name": table_name,
                **snapshot_table,
                "backend_table_spec": {"backend": "clickhouse", **snap_opts},
            },
            "to_table": _table_to_state_entry(model_table),
            "drop_old_after_swap": False,
            "preserve_old_suffix": "__dbw_old",
            "failed_suffix": "__dbw_failed",
        })
        rollback_ops.append({
            "type": "recreate_ch_table",
            "table": table_name,
            "reason": reason,
            "from_table": _table_to_state_entry(model_table),
            "to_table": {
                "name": table_name,
                **snapshot_table,
                "backend_table_spec": {"backend": "clickhouse", **snap_opts},
            },
            "drop_old_after_swap": False,
            "preserve_old_suffix": "__dbw_failed",
            "failed_suffix": "__dbw_old",
        })
        return

    if ch_changes:
        upgrade_ops.append({
            "type": "alter_ch_options",
            "table": table_name,
            "changes": ch_changes,
        })
        rollback_ops.append({
            "type": "alter_ch_options",
            "table": table_name,
            "changes": {k: {"from": v["to"], "to": v["from"]} for k, v in ch_changes.items()},
        })


_CH_COLUMN_KEYS: frozenset[str] = frozenset({
    "ch_codec",
    "ch_default_expression",
    "ch_materialized",
    "ch_alias",
    "ch_ttl",
    "ch_low_cardinality",
    "ch_nullable",
    "ch_type",
})


def _diff_ch_column_extras(
    snap_ch_col: dict,
    model_ch_col: dict,
    table_name: str,
    col_name: str,
    upgrade_ops: list[dict],
    rollback_ops: list[dict],
) -> None:
    if json.dumps(snap_ch_col, sort_keys=True, default=str) != json.dumps(model_ch_col, sort_keys=True, default=str):
        upgrade_ops.append({
            "type": "alter_ch_column",
            "table": table_name,
            "column": col_name,
            "from_ch_column": snap_ch_col,
            "to_ch_column": model_ch_col,
        })
        rollback_ops.append({
            "type": "alter_ch_column",
            "table": table_name,
            "column": col_name,
            "from_ch_column": model_ch_col,
            "to_ch_column": snap_ch_col,
        })


_SNAP_TO_MODEL_KEY = {
    "collation": "pg_collation",
    "storage": "pg_storage",
    "compression": "pg_compression",
    "generated": "pg_generated",
    "identity": "pg_identity",
    "identity_start": "pg_identity_start",
    "identity_increment": "pg_identity_increment",
    "identity_min": "pg_identity_min",
    "identity_max": "pg_identity_max",
}

def snap_to_model_key(snap_key: str) -> str:
    return _SNAP_TO_MODEL_KEY.get(snap_key, snap_key)


def _normalize_default(d: Any) -> str | None:
    if d is None:
        return None
    s = str(d).strip()
    while len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1]
    s = s.replace("\\'", "'").replace('\\"', '"')
    if s.upper() in ("TRUE", "FALSE"):
        s = s.upper()
    if s.upper() in ("NOW()", "CURRENT_TIMESTAMP()", "CURRENT_TIMESTAMP"):
        s = "CURRENT_TIMESTAMP"
    return s


def _normalize_mysql_default(d: Any) -> str | None:
    s = _normalize_default(d)
    if s is None:
        return None
    if s.upper().startswith("CURRENT_TIMESTAMP ON UPDATE "):
        return "CURRENT_TIMESTAMP"
    return s


def _normalize_mysql_table_value(key: str, value: Any) -> Any:
    if value is None and key in {"my_auto_increment", "my_row_format"}:
        return None
    if isinstance(value, str) and key in {"my_engine", "my_charset", "my_collate", "my_row_format"}:
        return value.lower()
    return value


def _mysql_column_definition_for_meta(
    col_type: str,
    meta: dict[str, Any],
    nullable: bool | None = None,
    default: str | None = None,
    comment: str | None = None,
    autoincrement: bool | None = None,
) -> str:
    _assert_complete_mysql_type(col_type)
    definition = col_type
    if meta.get("my_unsigned") and "UNSIGNED" not in definition.upper():
        definition = f"{definition} UNSIGNED"
    if autoincrement:
        definition += " AUTO_INCREMENT"
    if nullable is not None:
        definition += " NOT NULL" if not nullable else " NULL"
    if default is not None:
        definition += f" DEFAULT {default}"
    if comment is not None:
        escaped = comment.replace("'", "''")
        definition += f" COMMENT '{escaped}'"
    if meta.get("my_charset"):
        definition += f" CHARACTER SET {meta['my_charset']}"
    if meta.get("my_collate"):
        definition += f" COLLATE {meta['my_collate']}"
    if meta.get("my_on_update"):
        definition += f" ON UPDATE {meta['my_on_update']}"
    return definition


def diff_models_against_snapshot(
    model_tables: list[ModelTable],
    snapshot: dict[str, Any],
    database: str | None = None,
    db_name: str | None = None,
    clickhouse_engine_recreate: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    snapshot_tables = snapshot.get("tables", {})
    model_by_name = {t.name: t for t in model_tables}

    _SYSTEM_TABLE_PREFIXES = ("_dbwarden_", "dbwarden_lock")

    for table in model_tables:
        if table.name.startswith(_SYSTEM_TABLE_PREFIXES):
            continue
        if table.name not in snapshot_tables:
            upgrade_ops.append({
                "type": "create_table",
                "table": table.name,
                "object_type": table.object_type,
                "sql": None,
            })
            rollback_ops.append({
                "type": "drop_table",
                "table": table.name,
                "object_type": table.object_type,
            })

    for snap_table_name in list(snapshot_tables.keys()):
        if snap_table_name.startswith(_SYSTEM_TABLE_PREFIXES):
            continue
        if snap_table_name not in model_by_name:
            snap_object_type = snapshot_tables[snap_table_name].get("object_type", "table")
            upgrade_ops.append({
                "type": "drop_table",
                "table": snap_table_name,
                "object_type": snap_object_type,
            })
            rollback_ops.append({
                "type": "create_table",
                "table": snap_table_name,
                "object_type": snap_object_type,
                "sql": None,
            })

    for table in model_tables:
        if table.name.startswith(_SYSTEM_TABLE_PREFIXES):
            continue
        if table.name not in snapshot_tables:
            continue

        snap_table = snapshot_tables[table.name]
        snap_columns = snap_table.get("columns", {})
        model_columns = {c.name: c for c in table.columns}

        snap_comment = snap_table.get("comment")
        if snap_comment != table.comment:
            upgrade_ops.append({
                "type": "alter_table_comment",
                "table": table.name,
                "comment": table.comment,
                "previous_comment": snap_comment,
            })
            rollback_ops.append({
                "type": "alter_table_comment",
                "table": table.name,
                "comment": snap_comment,
            })

        snap_ch_options = snap_table.get("ch_options") or snap_table.get("clickhouse_options") or {}
        model_ch_options = table.clickhouse_options or {}
        _diff_ch_options(snap_ch_options, model_ch_options, table.name, upgrade_ops, rollback_ops, snapshot_table=snap_table, model_table=table, clickhouse_engine_recreate=clickhouse_engine_recreate)

        snap_my_table = snap_table.get("my_table") or {}
        model_my_table = table.my_table or {}
        for key in sorted(set(snap_my_table.keys()) | set(model_my_table.keys())):
            snap_val = _normalize_mysql_table_value(key, snap_my_table.get(key))
            model_val = _normalize_mysql_table_value(key, model_my_table.get(key))
            if key == "my_auto_increment" and model_val is None:
                continue
            if snap_val != model_val:
                upgrade_ops.append({
                    "type": "alter_my_table",
                    "table": table.name,
                    "key": key,
                    "from_value": snap_my_table.get(key),
                    "to_value": model_my_table.get(key),
                })
                rollback_ops.append({
                    "type": "alter_my_table",
                    "table": table.name,
                    "key": key,
                    "from_value": model_my_table.get(key),
                    "to_value": snap_my_table.get(key),
                })

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

        snap_pk_count_table = sum(
            1 for ec in snap_table.get("columns", {}).values()
            if ec.get("primary_key")
        )
        model_pk_count_table = sum(1 for c in table.columns if c.primary_key)

        for col_name in snap_columns:
            if col_name not in model_columns:
                continue
            if col_name in renamed_old or col_name in renamed_new:
                continue
            snap_col = snap_columns[col_name]
            model_col = model_columns[col_name]
            snap_raw = snap_col.get("type", "")
            if _get_backend(db_name) == "clickhouse":
                snap_raw = _strip_ch_type_wrappers(snap_raw)
                model_raw = model_col.ch_meta.get("ch_type", str(model_col.type))
                model_raw = _strip_ch_type_wrappers(model_raw)
            else:
                model_raw = _model_type_str(model_col.type)
            snap_type = normalize_type(snap_raw)["type"]
            model_type = normalize_type(model_raw)["type"]
            if snap_type != model_type:
                op_model_type = model_col.ch_meta.get("ch_type", model_col.type) if _get_backend(db_name) == "clickhouse" else model_col.type
                upgrade_ops.append({
                    "type": "alter_column_type",
                    "table": table.name,
                    "column": col_name,
                    "snap_type": snap_col.get("type", ""),
                    "model_type": op_model_type,
                })
                rollback_ops.append({
                    "type": "alter_column_type",
                    "table": table.name,
                    "column": col_name,
                    "snap_type": snap_col.get("type", ""),
                    "model_type": op_model_type,
                })
            snap_nullable = snap_col.get("nullable", True)
            if snap_nullable != model_col.nullable:
                upgrade_ops.append({
                    "type": "alter_column_nullable",
                    "table": table.name,
                    "column": col_name,
                    "nullable": model_col.nullable,
                    "col_type": model_col.type,
                })
                rollback_ops.append({
                    "type": "alter_column_nullable",
                    "table": table.name,
                    "column": col_name,
                    "nullable": snap_nullable,
                    "col_type": snap_col.get("type", ""),
                })
            snap_autoinc = snap_col.get("autoincrement", False)
            model_autoinc = model_col.autoincrement
            # Suppress autoincrement diffs for composite PK columns (likely join tables)
            # where autoincrement does not apply and emitting ALTERs is dangerous.
            pk_count = max(snap_pk_count_table, model_pk_count_table)
            if model_autoinc is not None and bool(snap_autoinc) != bool(model_autoinc):
                if pk_count > 1 and _get_backend(db_name) in ("mysql", "mariadb"):
                    pass  # skip - composite PK columns should not get autoincrement ALTERs
                else:
                    upgrade_ops.append({
                        "type": "alter_column_autoincrement",
                        "table": table.name,
                        "column": col_name,
                        "autoincrement": model_autoinc,
                        "col_type": model_col.type,
                        "nullable": model_col.nullable,
                    })
                    rollback_ops.append({
                        "type": "alter_column_autoincrement",
                        "table": table.name,
                        "column": col_name,
                        "autoincrement": bool(snap_autoinc),
                        "col_type": snap_col.get("type", ""),
                        "nullable": snap_nullable,
                    })
            snap_default = _normalize_default(snap_col.get("default"))
            model_default = _normalize_default(model_col.default)
            if _get_backend(db_name) in ("mysql", "mariadb"):
                snap_default = _normalize_mysql_default(snap_col.get("default"))
                model_default = _normalize_mysql_default(model_col.default)
                snap_my_col = snap_col.get("my_column") or {}
                model_my_col = model_col.my_meta or {}
                if snap_my_col.get("my_on_update") and model_my_col.get("my_on_update") and model_default is None and snap_default == "CURRENT_TIMESTAMP":
                    snap_default = None
            if snap_default != model_default:
                upgrade_ops.append({
                    "type": "alter_column_default",
                    "table": table.name,
                    "column": col_name,
                    "default": model_default,
                    "col_type": model_col.type,
                    "nullable": model_col.nullable,
                    "my_meta": model_col.my_meta or {},
                })
                rollback_ops.append({
                    "type": "alter_column_default",
                    "table": table.name,
                    "column": col_name,
                    "default": snap_default,
                    "col_type": snap_col.get("type", ""),
                    "nullable": snap_nullable,
                    "my_meta": snap_col.get("my_column", {}),
                })
            snap_col_comment = snap_col.get("comment")
            if snap_col_comment != model_col.comment:
                snap_my_col = snap_col.get("my_column") or {}
                model_my_col = model_col.my_meta or {}
                upgrade_ops.append({
                    "type": "alter_column_comment",
                    "table": table.name,
                    "column": col_name,
                    "comment": model_col.comment,
                    "previous_comment": snap_col_comment,
                    "col_type": model_col.type,
                    "nullable": model_col.nullable,
                    "autoincrement": model_col.autoincrement,
                    "my_meta": model_my_col,
                })
                rollback_ops.append({
                    "type": "alter_column_comment",
                    "table": table.name,
                    "column": col_name,
                    "comment": snap_col_comment,
                    "col_type": snap_col.get("type", ""),
                    "nullable": snap_nullable,
                    "autoincrement": snap_col.get("autoincrement", False),
                    "my_meta": snap_my_col,
                })
            snap_pg_col = snap_col.get("pg_column") or {}
            model_pg_meta = model_col.pg_meta or {}
            norm_snap_pg_col = {
                snap_to_model_key(k): v for k, v in snap_pg_col.items()
                if snap_to_model_key(k) not in ("pg_type",)
            }
            model_pg_meta_filtered = {
                k: v for k, v in model_pg_meta.items()
                if k not in ("pg_type", "pg_enum_name", "pg_enum_values")
            }
            if norm_snap_pg_col != model_pg_meta_filtered:
                upgrade_ops.append({
                    "type": "alter_pg_column_meta",
                    "table": table.name,
                    "column": col_name,
                    "col_type": model_col.type,
                    "snap_type": snap_col.get("type", ""),
                    "from_pg_column": snap_pg_col,
                    "to_pg_column": model_pg_meta,
                })
                rollback_ops.append({
                    "type": "alter_pg_column_meta",
                    "table": table.name,
                    "column": col_name,
                    "col_type": snap_col.get("type", ""),
                    "snap_type": model_col.type,
                    "from_pg_column": model_pg_meta,
                    "to_pg_column": snap_pg_col,
                })

            snap_ch_col = snap_col.get("ch_column") or {}
            model_ch_col = model_col.ch_meta or {}
            _diff_ch_column_extras(snap_ch_col, model_ch_col, table.name, col_name, upgrade_ops, rollback_ops)

            snap_my_col = snap_col.get("my_column") or {}
            model_my_col = model_col.my_meta or {}
            if snap_my_col != model_my_col:
                upgrade_ops.append({
                    "type": "alter_my_column_meta",
                    "table": table.name,
                    "column": col_name,
                    "col_type": model_col.type,
                    "snap_type": snap_col.get("type", ""),
                    "from_my_column": snap_my_col,
                    "to_my_column": model_my_col,
                    "nullable": model_col.nullable,
                    "default": model_col.default,
                    "comment": model_col.comment,
                    "autoincrement": model_col.autoincrement,
                    "snap_nullable": snap_col.get("nullable", True),
                    "snap_default": snap_col.get("default"),
                    "snap_comment": snap_col.get("comment"),
                })
                rollback_ops.append({
                    "type": "alter_my_column_meta",
                    "table": table.name,
                    "column": col_name,
                    "col_type": snap_col.get("type", ""),
                    "snap_type": model_col.type,
                    "from_my_column": model_my_col,
                    "to_my_column": snap_my_col,
                    "nullable": snap_col.get("nullable", True),
                    "default": snap_col.get("default"),
                    "comment": snap_col.get("comment"),
                    "autoincrement": snap_col.get("autoincrement", False),
                    "snap_nullable": model_col.nullable,
                    "snap_default": model_col.default,
                    "snap_comment": model_col.comment,
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

        # --- Constraint diff (unique, check, exclude) ---
        table_constraints = snapshot.get("constraints", {})
        snap_uniques = {
            c.get("name", name): c for name, c in table_constraints.items()
            if c.get("type") == "unique" and c.get("table") == table.name
        }
        model_uniques = {u.get("name") or f"uq_{table.name}_{'_'.join(u.get('columns', []))}": u for u in (table.uniques or [])}

        # RENAME CONSTRAINT optimization: same columns, different name
        snap_by_cols: dict[frozenset, tuple[str, dict]] = {}
        model_by_cols: dict[frozenset, tuple[str, dict]] = {}
        for n, u in snap_uniques.items():
            snap_by_cols[frozenset(u.get("columns", []))] = (n, u)
        for n, u in model_uniques.items():
            model_by_cols[frozenset(u.get("columns", []))] = (n, u)
        handled_snap: set[str] = set()
        handled_model: set[str] = set()
        for cols_sig, (snap_name, snap_entry) in snap_by_cols.items():
            model_match = model_by_cols.get(cols_sig)
            if model_match is None:
                continue
            model_name, model_entry = model_match
            if snap_name == model_name:
                handled_snap.add(snap_name)
                handled_model.add(model_name)
            elif snap_entry.get("columns") == model_entry.get("columns"):
                # Same columns, different name: emit RENAME CONSTRAINT
                rename_payload = {"old_name": snap_name, "new_name": model_name, "columns": list(cols_sig)}
                upgrade_ops.append({"type": "rename_unique_constraint", "table": table.name, **rename_payload})
                rollback_ops.append({"type": "rename_unique_constraint", "table": table.name, "old_name": model_name, "new_name": snap_name, "columns": list(cols_sig)})
                handled_snap.add(snap_name)
                handled_model.add(model_name)
        for name, uq in snap_uniques.items():
            if name in handled_snap:
                continue
            if name not in model_uniques or snap_uniques[name] != model_uniques[name]:
                payload = {k: v for k, v in uq.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "drop_unique_constraint", "table": table.name, "name": name, **payload})
                rollback_ops.append({"type": "add_unique_constraint", "table": table.name, "name": name, **payload})
        for name, uq in model_uniques.items():
            if name in handled_model:
                continue
            if name not in snap_uniques:
                payload = {k: v for k, v in uq.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "add_unique_constraint", "table": table.name, "name": name, **payload})
                rollback_ops.append({"type": "drop_unique_constraint", "table": table.name, "name": name, **payload})

        snap_checks = {
            c.get("name", name): c for name, c in table_constraints.items()
            if c.get("type") == "check" and c.get("table") == table.name
        }
        model_checks = {c.get("name") or f"ck_{table.name}_{i}": c for i, c in enumerate(table.checks or [])}
        for name, ck in snap_checks.items():
            snap_sig = {k: v for k, v in ck.items() if k not in {"type", "table", "columns"}}
            model_sig = model_checks.get(name, {})
            if name not in model_checks or snap_sig != model_sig:
                payload = {k: v for k, v in ck.items() if k not in {"type", "table"}}
                upgrade_ops.append({"type": "drop_check_constraint", "table": table.name, "name": name, **payload})
                rollback_ops.append({"type": "add_check_constraint", "table": table.name, "name": name, **payload})
        for name, ck in model_checks.items():
            if name not in snap_checks:
                upgrade_ops.append({"type": "add_check_constraint", "table": table.name, "name": name, **ck})
                rollback_ops.append({"type": "drop_check_constraint", "table": table.name, "name": name, **ck})

        # --- Table-level PG metadata diff (pg_table) ---
        snap_pg_table = snapshot_tables[table.name].get("pg_table", {}) or {}
        model_pg_table = table.pg_table or {}
        scalar_keys = {k for k in set(snap_pg_table.keys()) | set(model_pg_table.keys()) if k != "pg_excludes"}
        for key in sorted(scalar_keys):
            if snap_pg_table.get(key) != model_pg_table.get(key):
                upgrade_ops.append({
                    "type": "alter_pg_table",
                    "table": table.name,
                    "key": key,
                    "from_value": snap_pg_table.get(key),
                    "to_value": model_pg_table.get(key),
                })
                rollback_ops.append({
                    "type": "alter_pg_table",
                    "table": table.name,
                    "key": key,
                    "from_value": model_pg_table.get(key),
                    "to_value": snap_pg_table.get(key),
                })

        snap_excl_list = snap_pg_table.get("pg_excludes", []) or []
        model_excl_list = model_pg_table.get("pg_excludes", []) or []
        snap_excludes = {e["name"]: e for e in snap_excl_list}
        model_excludes = {e["name"]: e for e in model_excl_list}

        for name, ex in snap_excludes.items():
            if name not in model_excludes or snap_excludes[name] != model_excludes.get(name):
                upgrade_ops.append({
                    "type": "drop_exclude_constraint",
                    "table": table.name,
                    "name": name,
                    "expression": ex.get("expression", ""),
                })
                rollback_ops.append({
                    "type": "add_exclude_constraint",
                    "table": table.name,
                    "name": name,
                    "expression": ex.get("expression", ""),
                })
        for name, ex in model_excludes.items():
            if name not in snap_excludes:
                upgrade_ops.append({
                    "type": "add_exclude_constraint",
                    "table": table.name,
                    "name": name,
                    "expression": ex.get("expression", ""),
                })
                rollback_ops.append({
                    "type": "drop_exclude_constraint",
                    "table": table.name,
                    "name": name,
                    "expression": ex.get("expression", ""),
                })

    # --- FK diff ---
    def _fk_sig(fk: dict) -> tuple:
        return (
            frozenset(fk.get("columns", [])),
            fk.get("referenced_table") or fk.get("referred_table", ""),
            frozenset(fk.get("referenced_columns", fk.get("referred_columns", []))),
            fk.get("on_delete", "NO ACTION"),
            fk.get("on_update", "NO ACTION"),
            bool(fk.get("deferrable", False)),
        )

    snapshot_constraints = snapshot.get("constraints", {})
    for table in model_tables:
        model_fks = table.foreign_keys or []
        model_fk_sigs = {_fk_sig(fk) for fk in model_fks}

        snap_fks = [
            c for c in snapshot_constraints.values()
            if c.get("type") == "foreign_key" and c.get("table") == table.name
        ]
        snap_fk_sigs = {_fk_sig(fk) for fk in snap_fks}

        for fk in snap_fks:
            if _fk_sig(fk) not in model_fk_sigs:
                upgrade_ops.append({
                    "type": "drop_foreign_key",
                    "table": table.name,
                    "columns": fk["columns"],
                    "referenced_table": fk["referenced_table"],
                    "referenced_columns": fk["referenced_columns"],
                })
                rollback_ops.append({
                    "type": "add_foreign_key",
                    "table": table.name,
                    "columns": fk["columns"],
                    "referenced_table": fk["referenced_table"],
                    "referenced_columns": fk["referenced_columns"],
                    "on_delete": fk.get("on_delete", "NO ACTION"),
                    "on_update": fk.get("on_update", "NO ACTION"),
                    "deferrable": bool(fk.get("deferrable", False)),
                })

        for fk in model_fks:
            if _fk_sig(fk) not in snap_fk_sigs:
                ref_table = fk.get("referred_table") or fk.get("referenced_table", "")
                snap_tbl = snapshot.get("tables", {}).get(ref_table)
                if snap_tbl is None:
                    continue
                snap_ref_cols = snap_tbl.get("columns", {})
                ref_cols = fk["referred_columns"]
                if not all(c in snap_ref_cols for c in ref_cols):
                    continue
                upgrade_ops.append({
                    "type": "add_foreign_key",
                    "table": table.name,
                    "columns": fk["columns"],
                    "referenced_table": fk["referred_table"],
                    "referenced_columns": fk["referred_columns"],
                    "on_delete": fk.get("on_delete", "NO ACTION"),
                    "on_update": fk.get("on_update", "NO ACTION"),
                    "deferrable": fk.get("deferrable", False),
                })
                rollback_ops.append({
                    "type": "drop_foreign_key",
                    "table": table.name,
                    "columns": fk["columns"],
                    "referenced_table": fk["referred_table"],
                    "referenced_columns": fk["referred_columns"],
                })

    # --- Index diff ---
    snapshot_indexes = snapshot.get("indexes", {})
    for table in model_tables:
        model_idxs = table.indexes or []
        model_idx_sigs = {_index_sig(idx) for idx in model_idxs}

        # Snapshot indexes for this table
        snap_idxs = [
            (idx.get("name", ""), idx) for _, idx in snapshot_indexes.items()
            if idx.get("table") == table.name
        ]
        snap_idx_sigs = {_index_sig(idx) for _, idx in snap_idxs}

        # Indexes to drop (in snapshot but not in model)
        for name, idx in snap_idxs:
            sig = _index_sig(idx)
            if sig not in model_idx_sigs:
                upgrade_ops.append({
                    "type": "drop_index",
                    "table": table.name,
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
                })
                rollback_ops.append({
                    "type": "add_index",
                    "table": table.name,
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
                })

        # Indexes to add (in model but not in snapshot)
        for idx in model_idxs:
            sig = _index_sig(idx)
            if sig not in snap_idx_sigs:
                upgrade_ops.append(_index_op_from_info(idx, table.name))
                rollback_ops.append({
                    "type": "drop_index",
                    "table": table.name,
                    "index_name": None,
                    "columns": idx.columns,
                    "unique": idx.unique,
                })

    # --- Enum ADD VALUE diff ---
    snap_enums = snapshot.get("enums", {})
    model_enum_values: dict[str, list[str]] = {}
    for table in model_tables:
        for col in table.columns:
            pg_type = col.pg_meta.get("pg_type", {})
            if pg_type.get("kind") == "enum":
                type_name = pg_type.get("type_name", "")
                if type_name:
                    model_enum_values[type_name] = pg_type.get("values", [])
    for enum_name, snap_values in snap_enums.items():
        to_values = model_enum_values.get(enum_name)
        if to_values is None:
            continue
        snap_set = set(snap_values)
        new_values = [v for v in to_values if v not in snap_set]
        if new_values:
            pos_map = {v: i for i, v in enumerate(to_values)}
            for v in new_values:
                idx = pos_map[v]
                after = to_values[idx - 1] if idx > 0 else None
                upgrade_ops.append({
                    "type": "alter_enum_add_value",
                    "enum_name": enum_name,
                    "value": v,
                    "after": after,
                })
                rollback_ops.append({
                    "type": "alter_enum_add_value",
                    "enum_name": enum_name,
                    "value": v,
                    "revert": True,
                    "after": after,
                })

    # --- End Enum ADD VALUE diff ---

    # --- Annotate recreate_ch_table ops with dependent MVs ---
    for op in upgrade_ops + rollback_ops:
        if op.get("type") == "recreate_ch_table":
            tname = op["table"]
            mvs = sorted(
                mt.name for mt in model_tables
                if mt.clickhouse_options.get("ch_to_table") == tname
                and snapshot_tables.get(mt.name, {}).get("clickhouse_options", {}).get("ch_to_table") == tname
            )
            if mvs:
                op["dependent_mvs"] = mvs

    recreate_tables = {op["table"] for op in upgrade_ops if op.get("type") == "recreate_ch_table"}
    if recreate_tables:
        allowed = {"recreate_ch_table", "drop_table", "create_table", "rename_table", "alter_enum_add_value"}
        upgrade_ops = [op for op in upgrade_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]
        rollback_ops = [op for op in rollback_ops if op.get("table") not in recreate_tables or op.get("type") in allowed]

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
            found = False
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
                    found = True
                    break
                break
            if not found:
                import logging
                logging.getLogger("dbwarden.snapshot").warning(
                    "Confirmed rename %s.%s -> %s could not be applied: "
                    "no matching drop+add pair found.",
                    table, old, new,
                )

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
    safe_type_change: bool = False,
    concurrent: bool = True,
    postgres_auto_using: bool = False,
) -> tuple[str, str, list[Any]]:
    from dbwarden.engine.model_discovery import (
        generate_add_column_sql,
        generate_create_table_sql,
        generate_drop_object_sql,
        _format_clickhouse_expression,
    )
    from dbwarden.engine.offline import reconstruct_model_table
    from dbwarden.engine.migration_name import Change

    statements: list[MigrationStatement] = []
    changes: list[Change] = []
    backend = _get_backend(db_name)

    # Apply global concurrent flag to all index ops
    if not concurrent:
        for op in upgrade_ops:
            if op["type"] in ("add_index", "drop_index"):
                op["concurrently"] = False
        for op in rollback_ops:
            if op["type"] in ("add_index", "drop_index"):
                op["concurrently"] = False

    for op in upgrade_ops:
        if op["type"] == "rename_table":
            intent = TableRenameIntent(old_table=op["old_table"], new_table=op["new_table"])
            stmt = _rename_table_sql(intent, backend)
            statements.append(stmt)
            changes.append(Change(
                operation="rename_table", table=op["old_table"], target=op["new_table"],
                resolved_from=op.get("resolved_from"),
            ))
        elif op["type"] == "recreate_ch_table":
            for stmt in _build_clickhouse_recreate_table_sql(op, db_name):
                statements.append(stmt)
            changes.append(Change(operation="recreate_ch_table", table=op["table"]))
        elif op["type"] == "create_table":
            table = reconstruct_model_table(op["state_table"]) if op.get("state_table") else _find_model_table(op["table"], db_name=db_name)
            if table:
                sql = generate_create_table_sql(table, db_name)
                statements.append(MigrationStatement(
                    order=StatementOrder.CREATE_TABLE,
                    upgrade_sql=sql,
                    rollback_sql=generate_drop_object_sql(table),
                ))
                changes.append(Change(operation="create_table", table=op["table"]))
        elif op["type"] == "drop_table":
            drop_table = reconstruct_model_table(op["state_table"]) if op.get("state_table") else ModelTable(name=op["table"], columns=[], object_type=op.get("object_type", "table"))
            rollback_sql = generate_create_table_sql(drop_table, db_name) if op.get("state_table") else f"CREATE TABLE {op['table']} (/* see .dbwarden/schemas/ for DDL */)"
            statements.append(MigrationStatement(
                order=StatementOrder.DROP_TABLE,
                upgrade_sql=generate_drop_object_sql(drop_table),
                rollback_sql=rollback_sql,
            ))
            changes.append(Change(operation="drop_table", table=op["table"]))
        elif op["type"] == "rename_column":
            statements.append(MigrationStatement(
                order=StatementOrder.RENAME_COLUMN,
                upgrade_sql=f"ALTER TABLE {op['table']} RENAME COLUMN {op['old_name']} TO {op['new_name']}",
                rollback_sql=f"ALTER TABLE {op['table']} RENAME COLUMN {op['new_name']} TO {op['old_name']}",
            ))
            changes.append(Change(
                operation="rename_column", table=op["table"], target=op["new_name"],
                resolved_from=op.get("resolved_from"),
            ))
        elif op["type"] == "add_column":
            model_col = op.get("model_column")
            if model_col:
                sql = generate_add_column_sql(op["table"], model_col, db_name)
                statements.append(MigrationStatement(
                    order=StatementOrder.ADD_COLUMN,
                    upgrade_sql=sql,
                    rollback_sql=f"ALTER TABLE {op['table']} DROP COLUMN {op['column']}",
                ))
            else:
                col_def = op.get("definition", {})
                col_type = col_def.get("type")
                if not col_type:
                    col_type = _missing_def_placeholder(backend)
                statements.append(MigrationStatement(
                    order=StatementOrder.ADD_COLUMN,
                    upgrade_sql=f"ALTER TABLE {op['table']} ADD COLUMN {op['column']} {col_type}",
                    rollback_sql=f"ALTER TABLE {op['table']} DROP COLUMN {op['column']}",
                ))
            changes.append(Change(operation="add_column", table=op["table"], target=op["column"]))
        elif op["type"] == "drop_column":
            warning = f"-- WARNING: DROPPING COLUMN {op['table']}.{op['column']}\n"
            col_type = op.get("definition", {}).get("type", "")
            if not col_type:
                col_type = _missing_def_placeholder(backend)
            statements.append(MigrationStatement(
                order=StatementOrder.DROP_COLUMN,
                upgrade_sql=f"{warning}ALTER TABLE {op['table']} DROP COLUMN {op['column']}",
                rollback_sql=f"ALTER TABLE {op['table']} ADD COLUMN {op['column']} {col_type}",
            ))
            changes.append(Change(operation="drop_column", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_column_type":
            model_type = op.get("model_type", "")
            if not isinstance(model_type, str):
                model_type = _model_type_str(model_type)
            if safe_type_change:
                temp_col = f"{op['column']}_new"
                stmts = _build_safe_type_change_sql(op["table"], op["column"], model_type, backend)
                for s in stmts:
                    statements.append(s)
                changes.append(Change(operation="alter_column_type", table=op["table"], target=op["column"]))
            else:
                alter_up, alter_rb = _build_alter_type_sql(op["table"], op["column"], model_type, backend, old_type=op.get("snap_type", ""), postgres_auto_using=postgres_auto_using)
                statements.append(MigrationStatement(
                    order=StatementOrder.ALTER_COLUMN_TYPE,
                    upgrade_sql=alter_up,
                    rollback_sql=alter_rb,
                ))
                changes.append(Change(operation="alter_column_type", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_column_nullable":
            nullable = op.get("nullable", True)
            col_type = op.get("col_type", "")
            null_up, null_rb = _build_alter_nullable_sql(op["table"], op["column"], nullable, col_type, backend)
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_COLUMN_NULLABLE,
                upgrade_sql=null_up,
                rollback_sql=null_rb,
            ))
            changes.append(Change(operation="alter_column_nullable", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_column_default":
            default = op.get("default")
            col_type = op.get("col_type")
            nullable = op.get("nullable")
            my_meta = op.get("my_meta", {})
            def_up, def_rb = _build_alter_default_sql(
                op["table"], op["column"], default, backend,
                col_type=col_type, nullable=nullable, my_meta=my_meta,
            )
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_COLUMN_DEFAULT,
                upgrade_sql=def_up,
                rollback_sql=def_rb,
            ))
            changes.append(Change(operation="alter_column_default", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_column_autoincrement":
            table = op["table"]
            column = op["column"]
            autoinc = op.get("autoincrement", False)
            col_type = op.get("col_type", "integer")
            seq_name = f"{table}_{column}_seq"
            if backend == "postgresql":
                if autoinc:
                    upgrade_sql = (
                        f"CREATE SEQUENCE IF NOT EXISTS {seq_name};\n"
                        f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT nextval('{seq_name}');\n"
                        f"ALTER SEQUENCE {seq_name} OWNED BY {table}.{column};"
                    )
                    rollback_sql = (
                        f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT;\n"
                        f"DROP SEQUENCE IF EXISTS {seq_name};"
                    )
                else:
                    upgrade_sql = (
                        f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT;\n"
                        f"DROP SEQUENCE IF EXISTS {seq_name};"
                    )
                    rollback_sql = (
                        f"CREATE SEQUENCE IF NOT EXISTS {seq_name};\n"
                        f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT nextval('{seq_name}');\n"
                        f"ALTER SEQUENCE {seq_name} OWNED BY {table}.{column};"
                    )
            elif backend in ("mysql", "mariadb"):
                nullable = op.get("nullable")
                null_clause = ""
                if nullable is not None:
                    null_clause = " NOT NULL" if not nullable else " NULL"
                if autoinc:
                    upgrade_sql = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type}{null_clause} AUTO_INCREMENT;"
                    rollback_sql = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type}{null_clause};"
                else:
                    upgrade_sql = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type}{null_clause};"
                    rollback_sql = f"ALTER TABLE {table} MODIFY COLUMN {column} {col_type}{null_clause} AUTO_INCREMENT;"
            else:
                upgrade_sql = f"-- Autoincrement toggle for {table}.{column} only supported on PostgreSQL"
                rollback_sql = f"-- Autoincrement toggle for {table}.{column} only supported on PostgreSQL"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_COLUMN_AUTOINCREMENT,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
            ))
            changes.append(Change(operation="alter_column_autoincrement", table=table, target=column))
        elif op["type"] == "alter_table_comment":
            comment = op.get("comment") or ""
            prev = op.get("previous_comment") or ""
            raw_comment = op.get("comment")
            raw_prev = op.get("previous_comment")
            if backend == "sqlite":
                c = comment.replace(chr(39), chr(39)+chr(39))
                up = f"-- COMMENT ON TABLE {op['table']} IS '{c}';" if comment else f"-- COMMENT ON TABLE {op['table']} IS NULL;"
                rb = f"-- COMMENT ON TABLE {op['table']} IS '{prev}';" if prev else f"-- COMMENT ON TABLE {op['table']} IS NULL;"
            elif backend in ("mysql", "mariadb"):
                c = (raw_comment or "").replace(chr(39), chr(39)+chr(39))
                p = (raw_prev or "").replace(chr(39), chr(39)+chr(39))
                up = f"ALTER TABLE {op['table']} COMMENT = '{c}';"
                rb = f"ALTER TABLE {op['table']} COMMENT = '{p}';"
            else:
                up = f"COMMENT ON TABLE {op['table']} IS '{comment.replace(chr(39), chr(39)+chr(39))}';" if comment else f"COMMENT ON TABLE {op['table']} IS NULL;"
                rb = f"COMMENT ON TABLE {op['table']} IS '{prev.replace(chr(39), chr(39)+chr(39))}';" if prev else f"COMMENT ON TABLE {op['table']} IS NULL;"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_COMMENT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation="alter_table_comment", table=op["table"]))
        elif op["type"] == "alter_column_comment":
            comment = op.get("comment") or ""
            prev = op.get("previous_comment") or ""
            raw_comment = op.get("comment")
            raw_prev = op.get("previous_comment")
            col_type = op.get("col_type", "")
            nullable = op.get("nullable")
            if backend == "sqlite":
                c = comment.replace(chr(39), chr(39)+chr(39))
                col = f"{op['table']}.{op['column']}"
                up = f"-- COMMENT ON COLUMN {col} IS '{c}';" if comment else f"-- COMMENT ON COLUMN {col} IS NULL;"
                rb = f"-- COMMENT ON COLUMN {col} IS '{prev}';" if prev else f"-- COMMENT ON COLUMN {col} IS NULL;"
            elif backend in ("mysql", "mariadb"):
                my_meta = op.get("my_meta", {}) or {}
                autoinc = op.get("autoincrement")
                up = (
                    f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} "
                    f"{_mysql_column_definition_for_meta(col_type, my_meta, nullable=nullable, comment=raw_comment, autoincrement=autoinc)};"
                )
                rb = (
                    f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} "
                    f"{_mysql_column_definition_for_meta(col_type, my_meta, nullable=nullable, comment=raw_prev, autoincrement=autoinc)};"
                )
            else:
                up = f"COMMENT ON COLUMN {op['table']}.{op['column']} IS '{comment.replace(chr(39), chr(39)+chr(39))}';" if comment else f"COMMENT ON COLUMN {op['table']}.{op['column']} IS NULL;"
                rb = f"COMMENT ON COLUMN {op['table']}.{op['column']} IS '{prev.replace(chr(39), chr(39)+chr(39))}';" if prev else f"COMMENT ON COLUMN {op['table']}.{op['column']} IS NULL;"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_COLUMN_COMMENT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation="alter_column_comment", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_ch_options":
            changes_map = op.get("changes", {})
            up_stmts: list[str] = []
            rb_stmts: list[str] = []
            for key, change in changes_map.items():
                to_val = change.get("to")
                from_val = change.get("from")
                if key == "ch_settings" and isinstance(to_val, dict):
                    for setting_key, setting_value in to_val.items():
                        up_stmts.append(f"ALTER TABLE {op['table']} MODIFY SETTING {setting_key} = {setting_value}")
                    if isinstance(from_val, dict):
                        for setting_key, setting_value in from_val.items():
                            rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY SETTING {setting_key} = {setting_value}")
                elif key == "ch_ttl" and to_val:
                    ttl_sql = ", ".join(to_val) if isinstance(to_val, list) else str(to_val)
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY TTL {ttl_sql}")
                    if from_val:
                        prev_ttl = ", ".join(from_val) if isinstance(from_val, list) else str(from_val)
                        rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY TTL {prev_ttl}")
                elif key == "ch_order_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY ORDER BY {_format_clickhouse_expression(to_val)}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY ORDER BY {_format_clickhouse_expression(from_val)}")
                elif key == "ch_primary_key" and to_val:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY PRIMARY KEY {_format_clickhouse_expression(to_val)}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY PRIMARY KEY {_format_clickhouse_expression(from_val)}")
                elif key == "ch_partition_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY PARTITION BY {to_val}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY PARTITION BY {from_val}")
                elif key == "ch_sample_by" and to_val:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY SAMPLE BY {to_val}")
                    if from_val:
                        rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY SAMPLE BY {from_val}")
                elif key == "ch_engine":
                    up_stmts.append(f"-- ENGINE change for {op['table']} requires table recreation")
                    rb_stmts.append(f"-- ENGINE change for {op['table']} requires table recreation")
                elif key == "ch_projections":
                    _build_ch_projection_sql(op['table'], to_val, from_val, up_stmts, rb_stmts)
                elif key in {"ch_select_statement", "ch_to_table", "ch_dictionary", "ch_dict_layout", "ch_dict_source", "ch_dict_lifetime", "ch_dict_primary_key", "ch_zookeeper_path", "ch_replica_name", "ch_object_type"}:
                    up_stmts.append(f"-- {key} changed for {op['table']}. Re-run with --clickhouse-engine-recreate to auto-generate recreation SQL.")
                    rb_stmts.append(f"-- {key} changed for {op['table']}. Re-run with --clickhouse-engine-recreate to auto-generate recreation SQL.")

            if up_stmts or rb_stmts:
                statements.append(MigrationStatement(
                    order=StatementOrder.ALTER_TABLE_OPTIONS,
                    upgrade_sql="\n".join(up_stmts) if up_stmts else "-- no-op",
                    rollback_sql="\n".join(rb_stmts) if rb_stmts else "-- no-op",
                ))
                changes.append(Change(operation="alter_ch_options", table=op["table"]))
        elif op["type"] == "alter_ch_column":
            from_ch = op.get("from_ch_column", {}) or {}
            to_ch = op.get("to_ch_column", {}) or {}
            base_type = to_ch.get("ch_type") or from_ch.get("ch_type") or ""
            up_stmts: list[str] = []
            rb_stmts: list[str] = []
            if to_ch.get("ch_type") and to_ch.get("ch_type") != from_ch.get("ch_type"):
                up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {to_ch['ch_type']}")
                if from_ch.get("ch_type"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {from_ch['ch_type']}")
            if to_ch.get("ch_codec") and to_ch.get("ch_codec") != from_ch.get("ch_codec"):
                up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {base_type} CODEC({to_ch['ch_codec']})")
                if from_ch.get("ch_codec"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {base_type} CODEC({from_ch['ch_codec']})")
            if to_ch.get("ch_default_expression") != from_ch.get("ch_default_expression"):
                if to_ch.get("ch_default_expression"):
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} DEFAULT {to_ch['ch_default_expression']}")
                else:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} REMOVE DEFAULT")
                if from_ch.get("ch_default_expression"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} DEFAULT {from_ch['ch_default_expression']}")
                else:
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} REMOVE DEFAULT")
            if to_ch.get("ch_materialized") != from_ch.get("ch_materialized"):
                if to_ch.get("ch_materialized"):
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} MATERIALIZED {to_ch['ch_materialized']}")
                if from_ch.get("ch_materialized"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} MATERIALIZED {from_ch['ch_materialized']}")
            if to_ch.get("ch_alias") != from_ch.get("ch_alias"):
                if to_ch.get("ch_alias"):
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} ALIAS {to_ch['ch_alias']}")
                if from_ch.get("ch_alias"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} ALIAS {from_ch['ch_alias']}")
            if to_ch.get("ch_ttl") != from_ch.get("ch_ttl"):
                if to_ch.get("ch_ttl"):
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} TTL {to_ch['ch_ttl']}")
                else:
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} REMOVE TTL")
                if from_ch.get("ch_ttl"):
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} TTL {from_ch['ch_ttl']}")
                else:
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} REMOVE TTL")
            _ch_type_changed = to_ch.get("ch_type") and to_ch.get("ch_type") != from_ch.get("ch_type")
            if not _ch_type_changed:
                ch_lc_diff = to_ch.get("ch_low_cardinality") != from_ch.get("ch_low_cardinality")
                ch_null_diff = to_ch.get("ch_nullable") != from_ch.get("ch_nullable")
                if ch_lc_diff or ch_null_diff:
                    base = _strip_ch_type_wrappers(to_ch.get("ch_type") or from_ch.get("ch_type") or "")
                    target = base
                    if to_ch.get("ch_low_cardinality"):
                        target = f"LowCardinality({target})"
                    if to_ch.get("ch_nullable"):
                        target = f"Nullable({target})"
                    up_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {target}")
                    base_rb = _strip_ch_type_wrappers(from_ch.get("ch_type") or to_ch.get("ch_type") or "")
                    rb_target = base_rb
                    if from_ch.get("ch_low_cardinality"):
                        rb_target = f"LowCardinality({rb_target})"
                    if from_ch.get("ch_nullable"):
                        rb_target = f"Nullable({rb_target})"
                    rb_stmts.append(f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} {rb_target}")

            if up_stmts or rb_stmts:
                statements.append(MigrationStatement(
                    order=StatementOrder.ALTER_COLUMN_TYPE,
                    upgrade_sql="\n".join(up_stmts) if up_stmts else "-- no-op",
                    rollback_sql="\n".join(rb_stmts) if rb_stmts else "-- no-op",
                ))
                changes.append(Change(operation="alter_ch_column", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_pg_column_meta":
            stmts = _build_pg_meta_sql(
                op["table"], op["column"], op["col_type"], op["snap_type"],
                op["to_pg_column"], op["from_pg_column"], backend,
            )
            for s in stmts:
                statements.append(s)
            changes.append(Change(operation="alter_pg_column_meta", table=op["table"], target=op["column"]))
        elif op["type"] == "alter_pg_table":
            key = op["key"]
            to_val = op.get("to_value")
            from_val = op.get("from_value")
            if backend == "postgresql":
                if key == "pg_fillfactor":
                    if to_val is not None:
                        up = f"ALTER TABLE {op['table']} SET (fillfactor = {to_val});"
                    else:
                        up = f"ALTER TABLE {op['table']} RESET (fillfactor);"
                    if from_val is not None:
                        rb = f"ALTER TABLE {op['table']} SET (fillfactor = {from_val});"
                    else:
                        rb = f"ALTER TABLE {op['table']} RESET (fillfactor);"
                    statements.append(MigrationStatement(
                        order=StatementOrder.ALTER_TABLE_OPTIONS,
                        upgrade_sql=up, rollback_sql=rb,
                    ))
                elif key == "pg_tablespace":
                    if to_val:
                        up = f"ALTER TABLE {op['table']} SET TABLESPACE {to_val};"
                    else:
                        up = f"-- Cannot unset tablespace for {op['table']}; move to default manually"
                    if from_val:
                        rb = f"ALTER TABLE {op['table']} SET TABLESPACE {from_val};"
                    else:
                        rb = f"-- Cannot restore tablespace for {op['table']}; move to default manually"
                    statements.append(MigrationStatement(
                        order=StatementOrder.ALTER_TABLE_OPTIONS,
                        upgrade_sql=up, rollback_sql=rb,
                    ))
                elif key == "pg_inherits":
                    if to_val:
                        parents = ", ".join(to_val)
                        up = f"ALTER TABLE {op['table']} INHERIT {parents};"
                    else:
                        up = f"-- Cannot remove all inheritance for {op['table']} via ALTER"
                    if from_val:
                        parents = ", ".join(from_val)
                        rb = f"ALTER TABLE {op['table']} INHERIT {parents};"
                    else:
                        rb = f"-- Cannot restore inheritance for {op['table']} via ALTER"
                    statements.append(MigrationStatement(
                        order=StatementOrder.ALTER_TABLE_OPTIONS,
                        upgrade_sql=up, rollback_sql=rb,
                    ))
                elif key == "pg_unlogged":
                    if to_val:
                        up = f"ALTER TABLE {op['table']} SET UNLOGGED;"
                    else:
                        up = f"ALTER TABLE {op['table']} SET LOGGED;"
                    if from_val:
                        rb = f"ALTER TABLE {op['table']} SET UNLOGGED;"
                    else:
                        rb = f"ALTER TABLE {op['table']} SET LOGGED;"
                    statements.append(MigrationStatement(
                        order=StatementOrder.ALTER_TABLE_OPTIONS,
                        upgrade_sql=up, rollback_sql=rb,
                    ))
                elif key == "pg_partition":
                    up = f"-- Partition strategy changed for {op['table']}; requires table rebuild"
                    rb = f"-- Cannot revert partition change for {op['table']}; requires table rebuild"
                    statements.append(MigrationStatement(
                        order=StatementOrder.ALTER_TABLE_OPTIONS,
                        upgrade_sql=up, rollback_sql=rb,
                    ))
            changes.append(Change(operation=f"alter_pg_table_{key}", table=op["table"]))
        elif op["type"] == "alter_my_table":
            key = op["key"]
            to_val = op.get("to_value")
            from_val = op.get("from_value")
            if backend in ("mysql", "mariadb"):
                if key == "my_engine":
                    up = f"ALTER TABLE {op['table']} ENGINE={to_val};" if to_val else f"-- Cannot unset engine for {op['table']}"
                    rb = f"ALTER TABLE {op['table']} ENGINE={from_val};" if from_val else f"-- Cannot restore unset engine for {op['table']}"
                elif key == "my_charset":
                    up = f"ALTER TABLE {op['table']} DEFAULT CHARACTER SET {to_val};" if to_val else f"-- Cannot unset character set for {op['table']}"
                    rb = f"ALTER TABLE {op['table']} DEFAULT CHARACTER SET {from_val};" if from_val else f"-- Cannot restore unset character set for {op['table']}"
                elif key == "my_collate":
                    up = f"ALTER TABLE {op['table']} COLLATE={to_val};" if to_val else f"-- Cannot unset collation for {op['table']}"
                    rb = f"ALTER TABLE {op['table']} COLLATE={from_val};" if from_val else f"-- Cannot restore unset collation for {op['table']}"
                elif key == "my_row_format":
                    up = f"ALTER TABLE {op['table']} ROW_FORMAT={to_val};" if to_val else f"-- Cannot unset row format for {op['table']}"
                    rb = f"ALTER TABLE {op['table']} ROW_FORMAT={from_val};" if from_val else f"-- Cannot restore unset row format for {op['table']}"
                elif key == "my_auto_increment":
                    up = f"ALTER TABLE {op['table']} AUTO_INCREMENT={to_val};" if to_val is not None else f"-- Cannot unset auto_increment for {op['table']}"
                    rb = f"ALTER TABLE {op['table']} AUTO_INCREMENT={from_val};" if from_val is not None else f"-- Cannot restore unset auto_increment for {op['table']}"
                else:
                    up = f"-- Unsupported MySQL table option change {key} on {op['table']}"
                    rb = up
                statements.append(MigrationStatement(
                    order=StatementOrder.ALTER_TABLE_OPTIONS,
                    upgrade_sql=up,
                    rollback_sql=rb,
                ))
            changes.append(Change(operation=f"alter_my_table_{key}", table=op["table"]))
        elif op["type"] == "alter_my_column_meta":
            from_my = op.get("from_my_column", {}) or {}
            to_my = op.get("to_my_column", {}) or {}
            if backend in ("mysql", "mariadb"):
                up = (
                    f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} "
                    f"{_mysql_column_definition_for_meta(op['col_type'], to_my,
                        nullable=op.get('nullable'),
                        default=op.get('default'),
                        comment=op.get('comment'),
                        autoincrement=op.get('autoincrement'))};"
                )
                rb = (
                    f"ALTER TABLE {op['table']} MODIFY COLUMN {op['column']} "
                    f"{_mysql_column_definition_for_meta(op['snap_type'], from_my,
                        nullable=op.get('snap_nullable'),
                        default=op.get('snap_default'),
                        comment=op.get('snap_comment'),
                        autoincrement=op.get('autoincrement'))};"
                )
                statements.append(MigrationStatement(
                    order=StatementOrder.ALTER_COLUMN_TYPE,
                    upgrade_sql=up,
                    rollback_sql=rb,
                ))
            changes.append(Change(operation="alter_my_column_meta", table=op["table"], target=op["column"]))
        elif op["type"] in ("add_unique_constraint", "drop_unique_constraint"):
            name = op["name"]
            using = op.get("using")
            using_clause = f" USING INDEX {using}" if using else ""
            if op["type"] == "add_unique_constraint":
                cols = ", ".join(op.get("columns", []))
                defer_clause = ""
                if backend == "postgresql" and op.get("deferrable"):
                    if op.get("initially_deferred"):
                        defer_clause = " DEFERRABLE INITIALLY DEFERRED"
                    else:
                        defer_clause = " DEFERRABLE INITIALLY IMMEDIATE"
                up = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} UNIQUE ({cols}){using_clause}{defer_clause};"
                rb = f"ALTER TABLE {op['table']} DROP CONSTRAINT {name};"
            else:
                up = f"ALTER TABLE {op['table']} DROP CONSTRAINT {name};"
                cols = ", ".join(op.get("columns", []))
                defer_clause = ""
                if backend == "postgresql" and op.get("deferrable"):
                    if op.get("initially_deferred"):
                        defer_clause = " DEFERRABLE INITIALLY DEFERRED"
                    else:
                        defer_clause = " DEFERRABLE INITIALLY IMMEDIATE"
                rb = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} UNIQUE ({cols}){using_clause}{defer_clause};"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_CONSTRAINT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation=op["type"], table=op["table"]))
        elif op["type"] == "rename_unique_constraint":
            up = f"ALTER TABLE {op['table']} RENAME CONSTRAINT {op['old_name']} TO {op['new_name']};"
            rb = f"ALTER TABLE {op['table']} RENAME CONSTRAINT {op['new_name']} TO {op['old_name']};"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_CONSTRAINT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation=op["type"], table=op["table"]))
        elif op["type"] in ("add_check_constraint", "drop_check_constraint"):
            name = op["name"]
            no_inherit = " NO INHERIT" if (op.get("no_inherit") and backend == "postgresql") else ""
            if op["type"] == "add_check_constraint":
                expr = op.get("expression", "")
                up = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} CHECK ({expr}){no_inherit};"
                rb = f"ALTER TABLE {op['table']} DROP CONSTRAINT IF EXISTS {name};"
            else:
                up = f"ALTER TABLE {op['table']} DROP CONSTRAINT IF EXISTS {name};"
                expr = op.get("expression", "")
                rb = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} CHECK ({expr}){no_inherit};"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_CONSTRAINT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation=op["type"], table=op["table"]))
        elif op["type"] in ("add_exclude_constraint", "drop_exclude_constraint"):
            name = op["name"]
            if op["type"] == "add_exclude_constraint":
                expr = op.get("expression", "")
                up = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} EXCLUDE {expr};"
                rb = f"ALTER TABLE {op['table']} DROP CONSTRAINT {name};"
            else:
                up = f"ALTER TABLE {op['table']} DROP CONSTRAINT {name};"
                expr = op.get("expression", "")
                rb = f"ALTER TABLE {op['table']} ADD CONSTRAINT {name} EXCLUDE {expr};"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_CONSTRAINT,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation=op["type"], table=op["table"]))
        elif op["type"] in ("add_foreign_key", "drop_foreign_key"):
            stmts = _build_foreign_key_sql(op, backend)
            for s in stmts:
                statements.append(s)
            if op["type"] == "add_foreign_key":
                changes.append(Change(
                    operation="add_foreign_key", table=op["table"],
                    target=f"{op['referenced_table']}({','.join(op['referenced_columns'])})",
                ))
            else:
                changes.append(Change(
                    operation="drop_foreign_key", table=op["table"],
                ))
        elif op["type"] in ("add_index", "drop_index"):
            stmts = _build_index_sql(op, backend)
            for s in stmts:
                statements.append(s)
            if op["type"] == "add_index":
                target = ",".join(op["columns"])
                idx_type = op.get("using")
                changes.append(Change(
                    operation="add_index", table=op["table"], target=target,
                    index_type=idx_type,
                ))
            else:
                changes.append(Change(
                    operation="drop_index", table=op["table"],
                ))
        elif op["type"] == "alter_enum_add_value":
            enum_name = op["enum_name"]
            value = op["value"]
            after = op.get("after")
            after_clause = f" AFTER {after!r}" if after else ""
            if backend == "sqlite":
                up = f"-- ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
                rb = f"-- Revert: {value} was added to enum {enum_name}"
            elif op.get("revert"):
                up = f"-- Revert: {value} was added to enum {enum_name}"
                rb = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
            else:
                up = f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS {value!r}{after_clause};"
                rb = f"-- Revert: {value} was added to enum {enum_name}"
            statements.append(MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=up, rollback_sql=rb,
            ))
            changes.append(Change(operation="alter_enum_add_value", table=enum_name, target=value))

    upgrade_sql, rollback_sql = _assemble_migration(statements)
    return upgrade_sql, rollback_sql, changes


def _build_clickhouse_recreate_table_sql(op: dict[str, Any], db_name: str | None) -> list[MigrationStatement]:
    from dbwarden.engine.model_discovery import generate_create_table_sql, generate_drop_object_sql
    from dbwarden.engine.offline import reconstruct_model_table

    table_name = op["table"]
    from_table = reconstruct_model_table(op["from_table"])
    to_table = reconstruct_model_table(op["to_table"])

    # Dictionaries use DROP + CREATE instead of rename swap
    if from_table.object_type == "dictionary" or to_table.object_type == "dictionary":
        upgrade_sql = (
            f"{generate_drop_object_sql(from_table)};\n"
            f"{generate_create_table_sql(to_table, db_name)};"
        )
        rollback_sql = (
            f"{generate_drop_object_sql(to_table)};\n"
            f"{generate_create_table_sql(from_table, db_name)};"
        )
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
            )
        ]

    # Inline materialized views (no TO target) use DROP VIEW + CREATE MATERIALIZED VIEW
    if from_table.object_type == "materialized_view" or to_table.object_type == "materialized_view":
        upgrade_sql = (
            f"{generate_drop_object_sql(from_table)};\n"
            f"{generate_create_table_sql(to_table, db_name)};"
        )
        rollback_sql = (
            f"{generate_drop_object_sql(to_table)};\n"
            f"{generate_create_table_sql(from_table, db_name)};"
        )
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_TABLE_OPTIONS,
                upgrade_sql=upgrade_sql,
                rollback_sql=rollback_sql,
            )
        ]

    new_name = f"{table_name}__dbw_new"
    preserved_name = f"{table_name}{op.get('preserve_old_suffix', '__dbw_old')}"
    failed_name = f"{table_name}{op.get('failed_suffix', '__dbw_failed')}"
    drop_old_after_swap = bool(op.get("drop_old_after_swap", False))
    dependent_mvs: list[str] = op.get("dependent_mvs", [])

    copy_columns = [col.name for col in to_table.columns if any(src.name == col.name for src in from_table.columns)]
    copy_cols_sql = ", ".join(copy_columns)

    upgrade_parts = []
    if dependent_mvs:
        upgrade_parts.append("; ".join(f"DETACH TABLE {mv}" for mv in dependent_mvs) + ";")
    upgrade_parts += [
        generate_create_table_sql(ModelTable(
            name=new_name,
            columns=to_table.columns,
            clickhouse_options=to_table.clickhouse_options,
            object_type=to_table.object_type,
            foreign_keys=to_table.foreign_keys,
            indexes=to_table.indexes,
            comment=to_table.comment,
            checks=to_table.checks,
            uniques=to_table.uniques,
            excludes=to_table.excludes,
            pg_table=to_table.pg_table,
        ), db_name),
        f"INSERT INTO {new_name} ({copy_cols_sql}) SELECT {copy_cols_sql} FROM {table_name};",
        f"RENAME TABLE {table_name} TO {preserved_name}, {new_name} TO {table_name};",
    ]
    if drop_old_after_swap:
        upgrade_parts.append(generate_drop_object_sql(ModelTable(name=preserved_name, columns=[], object_type=to_table.object_type)))
    else:
        upgrade_parts.append(f"-- Preserved previous table as {preserved_name}. Drop it after validation:\n-- DROP TABLE {preserved_name};")

    if dependent_mvs:
        upgrade_parts.append("; ".join(f"ATTACH TABLE {mv}" for mv in dependent_mvs) + ";")

    rollback_parts = []
    if dependent_mvs:
        rollback_parts.append("; ".join(f"DETACH TABLE {mv}" for mv in dependent_mvs) + ";")
    rollback_parts.append(generate_create_table_sql(ModelTable(
        name=failed_name,
        columns=from_table.columns,
        clickhouse_options=from_table.clickhouse_options,
        object_type=from_table.object_type,
        foreign_keys=from_table.foreign_keys,
        indexes=from_table.indexes,
        comment=from_table.comment,
        checks=from_table.checks,
        uniques=from_table.uniques,
        excludes=from_table.excludes,
        pg_table=from_table.pg_table,
    ), db_name))
    rollback_copy_columns = [col.name for col in from_table.columns if any(dst.name == col.name for dst in to_table.columns)]
    rollback_cols_sql = ", ".join(rollback_copy_columns)
    rollback_parts.append(f"INSERT INTO {failed_name} ({rollback_cols_sql}) SELECT {rollback_cols_sql} FROM {table_name};")
    rollback_parts.append(f"RENAME TABLE {table_name} TO {preserved_name}, {failed_name} TO {table_name};")
    if dependent_mvs:
        rollback_parts.append("; ".join(f"ATTACH TABLE {mv}" for mv in dependent_mvs) + ";")
    rollback_parts.append(f"-- Preserved forward table as {preserved_name}. Drop it after validation:\n-- DROP TABLE {preserved_name};")

    return [
        MigrationStatement(
            order=StatementOrder.ALTER_TABLE_OPTIONS,
            upgrade_sql="\n".join(upgrade_parts),
            rollback_sql="\n".join(rollback_parts),
        )
    ]


def _build_fk_name(table: str, columns: list[str]) -> str:
    return f"{table}_{'_'.join(columns)}_fkey"


def _build_foreign_key_sql(op: dict[str, Any], backend: str) -> list[MigrationStatement]:
    table = op["table"]
    columns = op.get("columns", [])
    ref_table = op.get("referenced_table", "")
    ref_columns = op.get("referenced_columns", [])
    fk_name = _build_fk_name(table, columns)

    if op["type"] == "add_foreign_key":
        cols = ", ".join(columns)
        ref_cols = ", ".join(ref_columns)
        if backend == "sqlite":
            return [
                MigrationStatement(
                    order=StatementOrder.ALTER_FOREIGN_KEY,
                    upgrade_sql=(
                        f"-- SQLite: ADD CONSTRAINT {fk_name} FOREIGN KEY ({cols}) "
                        f"REFERENCES {ref_table}({ref_cols}) (not supported)\n"
                        f"-- Recreate the table with the constraint included."
                    ),
                    rollback_sql=f"-- (inverse requires manual migration)",
                ),
            ]
        upgrade = (
            f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} "
            f"FOREIGN KEY ({cols}) REFERENCES {ref_table}({ref_cols})"
        )
        on_delete = op.get("on_delete")
        on_update = op.get("on_update")
        if on_delete and on_delete != "NO ACTION":
            upgrade += f" ON DELETE {on_delete}"
        if on_update and on_update != "NO ACTION":
            upgrade += f" ON UPDATE {on_update}"
        if backend == "postgresql" and op.get("deferrable"):
            upgrade += " DEFERRABLE INITIALLY DEFERRED"
        upgrade += ";"
        rollback = f"ALTER TABLE {table} DROP CONSTRAINT {fk_name};"
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_FOREIGN_KEY,
                upgrade_sql=upgrade,
                rollback_sql=rollback,
            ),
        ]
    else:  # drop_foreign_key
        cols = ", ".join(columns)
        ref_cols = ", ".join(ref_columns)
        fk_sql = f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({cols}) REFERENCES {ref_table}({ref_cols})"
        on_delete = op.get("on_delete")
        on_update = op.get("on_update")
        if on_delete and on_delete != "NO ACTION":
            fk_sql += f" ON DELETE {on_delete}"
        if on_update and on_update != "NO ACTION":
            fk_sql += f" ON UPDATE {on_update}"
        if backend == "postgresql" and op.get("deferrable"):
            fk_sql += " DEFERRABLE INITIALLY DEFERRED"
        fk_sql += ";"

        if backend in ("mysql", "mariadb"):
            upgrade = f"ALTER TABLE {table} DROP FOREIGN KEY {fk_name};"
        elif backend == "sqlite":
            return [
                MigrationStatement(
                    order=StatementOrder.ALTER_FOREIGN_KEY,
                    upgrade_sql=(
                        f"-- SQLite: DROP CONSTRAINT {fk_name} (not supported)\n"
                        f"-- Recreate the table without the constraint."
                    ),
                    rollback_sql="-- (inverse requires manual migration)",
                ),
            ]
        else:
            upgrade = f"ALTER TABLE {table} DROP CONSTRAINT {fk_name};"
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_FOREIGN_KEY,
                upgrade_sql=upgrade,
                rollback_sql=fk_sql,
            ),
        ]


def _build_index_name(table: str, columns: list[str], unique: bool, using: str | None = None) -> str:
    prefix = "uq" if unique else "idx"
    cols = "_".join(columns)
    name = f"{prefix}_{table}_{cols}"
    if using and using != "btree":
        name += f"_{using}"
    return name


def _build_index_sql(op: dict[str, Any], backend: str) -> list[MigrationStatement]:
    table = op["table"]
    columns = op.get("columns", [])
    unique = op.get("unique", False)
    using = op.get("using")
    where = op.get("where")
    include = op.get("include")
    with_params = op.get("with_params")
    tablespace = op.get("tablespace")
    nulls_not_distinct = op.get("nulls_not_distinct", False)
    column_sorting = op.get("column_sorting")
    concurrently = op.get("concurrently", True)
    clickhouse_type = op.get("clickhouse_type")
    clickhouse_granularity = op.get("clickhouse_granularity")
    idx_name = op.get("index_name") or _build_index_name(table, columns, unique, using)

    if op["type"] == "add_index":
        if backend == "clickhouse" and clickhouse_type:
            upgrade = (
                f"ALTER TABLE {table} ADD INDEX {idx_name} "
                f"({', '.join(columns)}) "
                f"TYPE {clickhouse_type} "
                f"GRANULARITY {clickhouse_granularity or 1};"
            )
            rollback = f"ALTER TABLE {table} DROP INDEX {idx_name};"
            return [
                MigrationStatement(
                    order=StatementOrder.ALTER_INDEX,
                    upgrade_sql=upgrade,
                    rollback_sql=rollback,
                ),
            ]

        parts = ["CREATE"]
        if unique:
            parts.append("UNIQUE")
        parts.append("INDEX")
        if backend == "postgresql" and concurrently:
            parts.append("CONCURRENTLY")
        parts.append(idx_name)
        parts.append(f"ON {table}")

        if using and using != "btree":
            parts.append(f"USING {using}")

        # Column list with sort orders
        col_parts = []
        for col in columns:
            col_sql = col
            sorting = (column_sorting or {}).get(col, "")
            if sorting:
                col_sql += f" {sorting}"
            col_parts.append(col_sql)
        parts.append(f"({', '.join(col_parts)})")

        if include and backend == "postgresql":
            parts.append(f"INCLUDE ({', '.join(include)})")

        if with_params and backend == "postgresql":
            opts = ", ".join(f"{k} = {v}" for k, v in with_params.items())
            parts.append(f"WITH ({opts})")

        if tablespace and backend == "postgresql":
            parts.append(f"TABLESPACE {tablespace}")

        if where:
            parts.append(f"WHERE {where}")

        if nulls_not_distinct and backend == "postgresql":
            parts.append("NULLS NOT DISTINCT")

        upgrade = " ".join(parts) + ";"
        rollback = f"DROP INDEX {idx_name};"
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_INDEX,
                upgrade_sql=upgrade,
                rollback_sql=rollback,
            ),
        ]
    else:  # drop_index
        if backend == "clickhouse":
            upgrade = f"ALTER TABLE {table} DROP INDEX {idx_name};"
            ch_type = using.upper() if using else "MINMAX"
            ch_granularity = op.get("granularity", 1)
            rollback = (
                f"ALTER TABLE {table} ADD INDEX {idx_name} "
                f"({', '.join(columns)}) "
                f"TYPE {ch_type} "
                f"GRANULARITY {ch_granularity};"
            )
            return [
                MigrationStatement(
                    order=StatementOrder.ALTER_INDEX,
                    upgrade_sql=upgrade,
                    rollback_sql=rollback,
                ),
            ]
        upgrade = f"DROP INDEX {idx_name};"
        unique_clause = "UNIQUE " if unique else ""
        cols_list = ", ".join(columns)
        rollback_parts = ["CREATE"]
        if unique:
            rollback_parts.append("UNIQUE")
        rollback_parts.append("INDEX")
        if backend == "postgresql" and concurrently:
            rollback_parts.append("CONCURRENTLY")
        rollback_parts.append(idx_name)
        rollback_parts.append(f"ON {table}")

        if using and using != "btree":
            rollback_parts.append(f"USING {using}")

        col_parts_rb = []
        for col in columns:
            col_sql = col
            sorting = (column_sorting or {}).get(col, "")
            if sorting:
                col_sql += f" {sorting}"
            col_parts_rb.append(col_sql)
        rollback_parts.append(f"({', '.join(col_parts_rb)})")

        if include and backend == "postgresql":
            rollback_parts.append(f"INCLUDE ({', '.join(include)})")
        if with_params and backend == "postgresql":
            opts = ", ".join(f"{k} = {v}" for k, v in with_params.items())
            rollback_parts.append(f"WITH ({opts})")
        if tablespace and backend == "postgresql":
            rollback_parts.append(f"TABLESPACE {tablespace}")
        if where:
            rollback_parts.append(f"WHERE {where}")
        if nulls_not_distinct and backend == "postgresql":
            rollback_parts.append("NULLS NOT DISTINCT")

        rollback = " ".join(rollback_parts) + ";"
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_INDEX,
                upgrade_sql=upgrade,
                rollback_sql=rollback,
            ),
        ]


def _build_safe_type_change_sql(
    table: str,
    column: str,
    new_type: str,
    backend: str,
) -> list[MigrationStatement]:
    if backend == "sqlite":
        return [
            MigrationStatement(
                order=StatementOrder.ALTER_COLUMN_TYPE,
                upgrade_sql=(
                    f"-- SQLite safe type change not supported.\n"
                    f"-- Manually recreate {table} with new type for {column}."
                ),
                rollback_sql="-- (inverse requires manual migration)",
            ),
        ]

    temp_col = f"{column}__new"
    return [
        MigrationStatement(
            order=StatementOrder.ADD_COLUMN,
            upgrade_sql=f"ALTER TABLE {table} ADD COLUMN {temp_col} {new_type}",
            rollback_sql=f"ALTER TABLE {table} DROP COLUMN {temp_col}",
        ),
        MigrationStatement(
            order=StatementOrder.ALTER_COLUMN_DEFAULT,
            upgrade_sql=f"-- Data migration needed: UPDATE {table} SET {temp_col} = CAST({column} AS {new_type})",
            rollback_sql="-- (inverse requires manual migration)",
        ),
        MigrationStatement(
            order=StatementOrder.ALTER_COLUMN_DEFAULT,
            upgrade_sql=f"-- Manually verify {temp_col} before dropping {column}",
            rollback_sql="-- (inverse requires manual migration)",
        ),
        MigrationStatement(
            order=StatementOrder.DROP_COLUMN,
            upgrade_sql=f"-- After verification: ALTER TABLE {table} DROP COLUMN {column}; ALTER TABLE {table} RENAME COLUMN {temp_col} TO {column}",
            rollback_sql="-- (inverse requires manual migration)",
        ),
    ]


def _normalize_sql(s: str) -> str:
    return s.strip().rstrip(";").strip()


def _sql_into_statements(sql: str) -> list[str]:
    parts = [s.strip() for s in sql.split(";") if s.strip()]
    return [_normalize_sql(p) for p in parts]


def _filter_duplicates_from_snapshot_diff(
    upgrade_sql: str,
    rollback_sql: str,
    changes: list[Any],
    existing_statements: set[str],
) -> tuple[str, str, list[Any]]:
    normalized_existing: set[str] = set()
    for s in existing_statements:
        s = _normalize_sql(s)
        if s:
            normalized_existing.add(s)

    upgrade_parts = [s.strip() for s in upgrade_sql.split("\n\n") if s.strip()]
    rollback_parts = [s.strip() for s in rollback_sql.split("\n\n") if s.strip()]

    if len(upgrade_parts) != len(changes) or len(rollback_parts) != len(changes):
        import logging
        logging.getLogger("dbwarden.snapshot").warning(
            "Snapshot diff part count mismatch: %d upgrade, %d rollback, %d changes. "
            "Skipping duplicate filter to avoid misalignment.",
            len(upgrade_parts), len(rollback_parts), len(changes),
        )
        return upgrade_sql, rollback_sql, changes

    filtered_upgrade = []
    filtered_rollback = []
    filtered_changes = []

    for i, (up_sql, rb_sql) in enumerate(zip(upgrade_parts, rollback_parts)):
        normalized = _normalize_sql(up_sql)
        if normalized in normalized_existing:
            continue
        statements = _sql_into_statements(up_sql)
        if statements and all(s in normalized_existing for s in statements):
            continue
        filtered_upgrade.append(up_sql)
        filtered_rollback.append(rb_sql)
        filtered_changes.append(changes[i])

    return "\n\n".join(filtered_upgrade), "\n\n".join(filtered_rollback), filtered_changes


def _find_model_table(table_name: str, db_name: str | None = None) -> ModelTable | None:
    from dbwarden.config import get_database
    from dbwarden.engine.model_discovery import get_model_table_by_name

    config = get_database(db_name)
    model_paths = config.model_paths
    if model_paths is None:
        from dbwarden.engine.model_discovery import auto_discover_model_paths
        model_paths = auto_discover_model_paths()
    if not model_paths:
        return None

    if config.model_tables is not None and table_name not in config.model_tables:
        return None
    return get_model_table_by_name(table_name, model_paths, db_name=db_name)
