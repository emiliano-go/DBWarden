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

from dbwarden.engine.model_discovery import IndexInfo, ModelColumn, ModelTable, _is_expression


class StatementOrder(IntEnum):
    ROLE_MGMT = -5
    ALTER_DEFAULT_PRIVILEGES = -4
    CREATE_EXTENSION = -3
    CREATE_SCHEMA = -2
    CREATE_DOMAIN = -1
    CREATE_SEQUENCE = 0
    RENAME_TABLE = 1
    RENAME_COLUMN = 2
    ALTER_COLUMN_TYPE = 3
    ALTER_COLUMN_NULLABLE = 4
    ALTER_COLUMN_DEFAULT = 5
    CREATE_TYPE = 6
    CREATE_FUNCTION = 6
    CREATE_TABLE = 7
    CREATE_VIEW = 8
    ADD_COLUMN = 9
    ALTER_FOREIGN_KEY = 10
    DROP_VIEW = 11
    ALTER_INDEX = 12
    DROP_COLUMN = 13
    DROP_TABLE = 14
    ALTER_TABLE_COMMENT = 15
    ALTER_COLUMN_COMMENT = 16
    ALTER_TABLE_OPTIONS = 17
    ALTER_TABLE_CONSTRAINT = 18
    ALTER_CONSTRAINT = 19
    VALIDATE_CONSTRAINT = 19
    ALTER_COLUMN_AUTOINCREMENT = 20
    ALTER_PG_RLS = 21
    ALTER_PG_POLICY = 22
    ALTER_PG_GRANT = 23
    CREATE_STATISTICS = 24
    CREATE_TRIGGER = 24
    ALTER_VIEW = 99


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


def _strip_pg_expr_parens(expr: str | None) -> str | None:
    """Remove one layer of outer parentheses added by pg_get_expr().

    pg_get_expr wraps boolean expressions in extra parens, e.g.
    ``(owner_id = current_user_id())``.  Strip them so the expression
    matches the user-provided form stored in the model.
    """
    if not expr:
        return expr
    if expr.startswith('(') and expr.endswith(')'):
        depth = 0
        for i, ch in enumerate(expr):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth == 0 and i < len(expr) - 1:
                # Unbalanced — the parens do not wrap the whole expression
                return expr
        return expr[1:-1]
    return expr


def _normalize_view_def(sql: str | None) -> str | None:
    """Normalize a SQL view definition for stable comparison.

    PostgreSQL reformats view definitions through ``pg_get_viewdef``,
    producing different whitespace, keyword casing, trailing
    semicolons, auto-added AS aliases for computed columns, and
    schema qualification differences.  This function collapses
    whitespace, strips trailing semicolons, strips PG-injected
    AS aliases, removes schema qualifiers, and lowercases so that
    semantically identical definitions compare equal.
    """
    if not sql:
        return sql
    sql = re.sub(r'\s+', ' ', sql).strip()
    sql = sql.rstrip(';').strip()
    sql = re.sub(r'(\w+\([^)]*\))\s+AS\s+\w+', r'\1', sql, flags=re.IGNORECASE)
    sql = re.sub(r'(?<=\s)(\w+)\.(\w+)', r'\2', sql)
    return sql.lower()


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
    elif backend == "clickhouse":
        stripped = col_type
        if col_type and col_type.startswith("Nullable(") and col_type.endswith(")"):
            stripped = col_type[len("Nullable("):-1]
        if stripped:
            mod_type = f"Nullable({stripped})" if nullable else stripped
            rev_type = stripped if nullable else f"Nullable({stripped})"
            upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {mod_type}"
            rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {rev_type}"
        else:
            upgrade = rollback = f"-- ClickHouse: cannot alter nullability for {table}.{column} (no type info)"
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
        from sqlalchemy.pool import NullPool
        engine = create_engine(sqlalchemy_url, poolclass=NullPool)
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
    domains: dict[str, Any] = {}
    indexes: dict[str, Any] = {}
    constraints: dict[str, Any] = {}
    sequences: dict[str, Any] = {}
    composite_types: dict[str, Any] = {}
    functions: dict[str, Any] = {}
    roles: dict[str, Any] = {}
    default_privileges: dict[str, Any] = {}
    schema_grants: dict[str, Any] = {}
    event_triggers: dict[str, Any] = {}
    extended_stats: dict[str, Any] = {}

    pg_schema = None
    pg_version: tuple[int, int] | None = None
    if database_type == "postgresql":
        try:
            from dbwarden.config import get_database
            pg_schema = get_database(database).postgres_schema
        except Exception:
            pass
        try:
            _vc = engine.connect() if own_engine and engine is not None else connection
            ver_row = _vc.execute(text("SELECT current_setting('server_version_num')")).scalar()
            if ver_row:
                ver_int = int(ver_row)
                pg_version = (ver_int // 10000, (ver_int // 100) % 100)
            if own_engine and engine is not None:
                _vc.close()
        except Exception:
            pass

    inspect_kw = {"schema": pg_schema} if pg_schema else {}
    table_names = inspector.get_table_names(**inspect_kw)
    for table_name in table_names:
        _regclass_name = f"{pg_schema}.{table_name}" if pg_schema else table_name
        columns_info = inspector.get_columns(table_name, **inspect_kw)
        pk_info = inspector.get_pk_constraint(table_name, **inspect_kw)

        if database_type == "postgresql":
            try:
                _pg_conn = engine.connect() if own_engine and engine is not None else connection
                local_rows = _pg_conn.execute(
                    text(
                        "SELECT attname FROM pg_attribute "
                        "WHERE attrelid = CAST(:t AS regclass) "
                        "AND attnum > 0 AND NOT attisdropped AND attislocal"
                    ),
                    {"t": _regclass_name},
                ).fetchall()
                local_columns = {r[0] for r in local_rows}
                if local_columns:
                    columns_info = [col for col in columns_info if col.get("name") in local_columns]
                if own_engine:
                    _pg_conn.close()
            except Exception:
                pass

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
            "schema": pg_schema,
        }

        if database_type == "postgresql":
            try:
                table_comment = inspector.get_table_comment(table_name, **inspect_kw)
                if table_comment and table_comment.get("text"):
                    table_entry["comment"] = table_comment["text"]
            except Exception:
                pass

            _conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT") if own_engine and engine is not None else connection
            try:
                pg_table: dict[str, Any] = {"backend": "postgresql"}

                try:
                    rows = _conn.execute(
                        text("SELECT unnest(COALESCE(reloptions, '{}')) FROM pg_class WHERE oid = CAST(:t AS regclass)"),
                        {"t": _regclass_name},
                    ).fetchall()
                    params: dict[str, Any] = {}
                    storage_params: dict[str, Any] = {}
                    for row in rows:
                        kv = row[0].split("=", 1)
                        if len(kv) == 2:
                            key = f"pg_{kv[0]}"
                            val: Any = kv[1]
                            if val.isdigit():
                                val = int(val)
                            params[key] = val
                            storage_params[kv[0]] = val
                    if params:
                        pg_table.update(params)
                    if storage_params:
                        pg_table["pg_storage_params"] = storage_params
                except Exception:
                    pass

                try:
                    # Toast reloptions
                    toast_sql = (
                        "SELECT unnest(COALESCE("
                        "(SELECT reloptions FROM pg_class WHERE oid = c.reltoastrelid), '{}'"
                        ")) FROM pg_class c WHERE c.oid = CAST(:t AS regclass)"
                    )
                    toast_rows = _conn.execute(
                        text(toast_sql),
                        {"t": _regclass_name},
                    ).fetchall()
                    toast_params: dict[str, Any] = {}
                    for row in toast_rows:
                        kv = row[0].split("=", 1)
                        if len(kv) == 2:
                            key = f"toast.{kv[0]}"
                            val: Any = kv[1]
                            if val.isdigit():
                                val = int(val)
                            toast_params[key] = val
                    if toast_params:
                        existing = pg_table.get("pg_storage_params", {})
                        existing.update(toast_params)
                        pg_table["pg_storage_params"] = existing
                except Exception:
                    pass

                try:
                    row = _conn.execute(
                        text("SELECT relpersistence FROM pg_class WHERE oid = CAST(:t AS regclass)"),
                        {"t": _regclass_name},
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
                            "WHERE c.oid = CAST(:t AS regclass)"
                        ),
                        {"t": _regclass_name},
                    ).fetchone()
                    if row:
                        pg_table["pg_tablespace"] = row[0]
                except Exception:
                    pass

                try:
                    rows = _conn.execute(
                        text("""
                            SELECT p_ns.nspname AS parent_schema, p.relname AS parent_name
                            FROM pg_inherits i
                            JOIN pg_class c ON c.oid = i.inhrelid
                            JOIN pg_namespace c_ns ON c_ns.oid = c.relnamespace
                            JOIN pg_class p ON p.oid = i.inhparent
                            JOIN pg_namespace p_ns ON p_ns.oid = p.relnamespace
                            WHERE c.oid = CAST(:t AS regclass)
                        """),
                        {"t": _regclass_name},
                    ).fetchall()
                    parents = [r[1] for r in rows]
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
                            "WHERE c.oid = CAST(:t AS regclass) "
                            "GROUP BY p.partstrat, p.partexprs, p.partrelid"
                        ),
                        {"t": _regclass_name},
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
                        {"t": _regclass_name},
                    ).fetchall()
                    excludes = [{"name": r[0], "expression": r[1]} for r in rows]
                    if excludes:
                        pg_table["pg_excludes"] = excludes
                except Exception:
                    pass

                try:
                    child_rows = _conn.execute(
                        text("SELECT c.relname, pg_get_expr(c.relpartbound, c.oid) AS bound "
                             "FROM pg_class c JOIN pg_inherits i ON i.inhrelid = c.oid "
                             "WHERE i.inhparent = CAST(:t AS regclass) AND c.relispartition = true "
                             "ORDER BY c.relname"),
                        {"t": _regclass_name},
                    ).fetchall()
                    if child_rows:
                        children = [{"name": r[0], "bound": r[1]} for r in child_rows]
                        pg_table["pg_partitions"] = children
                except Exception as e:
                    import logging
                    logging.getLogger('dbwarden.snapshot').warning('child partitions extraction failed for %s: %s', _regclass_name, e)
                    try:
                        _conn.rollback()
                    except Exception:
                        pass

                try:
                    if pg_version and pg_version >= (14, 0):
                        attr_cols = "a.attname, a.attstorage, a.attcompression, a.attstattarget"
                    else:
                        attr_cols = "a.attname, a.attstorage, NULL::text AS attcompression, a.attstattarget"
                    rows = _conn.execute(
                        text(
                            f"SELECT {attr_cols} "
                            "FROM pg_attribute a "
                            "WHERE a.attrelid = CAST(:t AS regclass) AND a.attnum > 0 AND NOT a.attisdropped "
                            "ORDER BY a.attnum"
                        ),
                        {"t": _regclass_name},
                    ).fetchall()
                    storage_map = {'p': 'PLAIN', 'm': 'MAIN', 'e': 'EXTERNAL', 'x': 'EXTENDED'}
                    for r in rows:
                        cname = r[0]
                        if cname in columns_dict:
                            pg_col = columns_dict[cname].get("pg_column", {})
                            if isinstance(pg_col, dict):
                                storage = storage_map.get(r[1], r[1]) if r[1] else None
                                if storage and storage not in ("PLAIN", "EXTENDED"):
                                    pg_col["storage"] = storage
                                if r[2]:
                                    pg_col["compression"] = r[2]
                                if r[3] is not None and r[3] != -1:
                                    pg_col["statistics"] = r[3]
                                if pg_col:
                                    columns_dict[cname]["pg_column"] = pg_col
                except Exception as e:
                    import logging
                    logging.getLogger('dbwarden.snapshot').warning('attstats extraction failed for %s: %s', _regclass_name, e)
                    try:
                        _conn.rollback()
                    except Exception:
                        pass

                try:
                    row = _conn.execute(
                        text("SELECT relrowsecurity FROM pg_class WHERE oid = CAST(:t AS regclass)"),
                        {"t": _regclass_name},
                    ).fetchone()
                    if row and row[0]:
                        pg_table["pg_rls"] = True
                except Exception:
                    pass

                try:
                    row = _conn.execute(
                        text("SELECT relforcerowsecurity FROM pg_class WHERE oid = CAST(:t AS regclass)"),
                        {"t": _regclass_name},
                    ).fetchone()
                    if row and row[0]:
                        pg_table["pg_rls_force"] = True
                except Exception as e:
                    import logging
                    logging.getLogger('dbwarden.snapshot').warning('rls_force extraction failed for %s: %s', _regclass_name, e)
                    try:
                        _conn.rollback()
                    except Exception:
                        pass

                try:
                    policy_rows = _conn.execute(
                        text(
                            "SELECT policyname, permissive, cmd, roles, qual, with_check "
                            "FROM pg_policies "
                            "WHERE schemaname = :schema AND tablename = :table "
                            "ORDER BY policyname"
                        ),
                        {"schema": pg_schema or "public", "table": table_name},
                    ).fetchall()
                    if policy_rows:
                        policies = []
                        for r in policy_rows:
                            roles = list(r[3]) if r[3] else ["PUBLIC"]
                            policy_entry = {
                                "name": r[0],
                                "permissive": "PERMISSIVE" if r[1] else "RESTRICTIVE",
                                "command": r[2] or "ALL",
                                "role": roles[0] if len(roles) == 1 else roles,
                                "using": _strip_pg_expr_parens(r[4]),
                            }
                            if r[5]:
                                policy_entry["with_check"] = _strip_pg_expr_parens(r[5])
                            policies.append(policy_entry)
                        table_entry["pg_policies"] = policies
                except Exception:
                    pass

                try:
                    grant_rows = _conn.execute(
                        text(
                            "SELECT COALESCE(r.rolname, 'PUBLIC') AS grantee, "
                            "array_agg(acl.privilege_type ORDER BY acl.privilege_type) AS privileges, "
                            "bool_or(acl.is_grantable) AS grantable "
                            "FROM pg_class c "
                            "CROSS JOIN LATERAL aclexplode(c.relacl) AS acl "
                            "LEFT JOIN pg_roles r ON r.oid = acl.grantee "
                            "WHERE c.oid = CAST(:t AS regclass) "
                            "AND c.relacl IS NOT NULL "
                            "AND acl.grantee <> c.relowner "
                            "GROUP BY COALESCE(r.rolname, 'PUBLIC')"
                        ),
                        {"t": _regclass_name},
                    ).fetchall()
                    if grant_rows:
                        grants = []
                        for r in grant_rows:
                            grants.append({
                                "role": r[0],
                                "privileges": list(r[1]) if r[1] else ["ALL"],
                                "grantable": bool(r[2]),
                            })
                        table_entry["pg_grants"] = grants
                except Exception:
                    pass

                try:
                    trigger_rows = _conn.execute(
                        text("""
                            SELECT tgname, pg_get_triggerdef(t.oid) AS definition
                            FROM pg_trigger t
                            WHERE t.tgrelid = CAST(:t AS regclass) AND NOT t.tgisinternal
                            ORDER BY tgname
                        """),
                        {"t": _regclass_name},
                    ).fetchall()
                    if trigger_rows:
                        triggers = []
                        for r in trigger_rows:
                            triggers.append({
                                "name": r[0],
                                "definition": r[1],
                            })
                        table_entry["pg_triggers"] = triggers
                except Exception as e:
                    import logging
                    logging.getLogger('dbwarden.snapshot').warning('trigger extraction failed for %s: %s', _regclass_name, e)
                    try:
                        _conn.rollback()
                    except Exception:
                        pass

                if pg_table:
                    table_entry["pg_table"] = pg_table
            except Exception:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('PG table extraction failed for %s', _regclass_name)
                try:
                    _conn.rollback()
                except Exception:
                    pass
            finally:
                if own_engine and _conn is not None:
                    try:
                        _conn.rollback()
                    except Exception:
                        pass
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

        for idx in inspector.get_indexes(table_name, **inspect_kw):
            idx_name = idx.get("name", "")
            if not idx_name:
                continue
            if idx.get("unique") and set(idx.get("column_names", [])) == pk_columns:
                continue
            raw_cols = list(idx.get("column_names", []))
            raw_exprs = list(idx.get("expressions", []))
            expr = None
            clean_cols: list[str] = []
            if raw_exprs:
                for c in raw_cols:
                    if c is not None:
                        clean_cols.append(c)
                exprs = [e for e in raw_exprs if e is not None]
                if len(exprs) == 1 and not clean_cols:
                    expr = exprs[0]
                else:
                    clean_cols.extend(exprs)
            else:
                for c in raw_cols:
                    if _is_expression(c):
                        expr = c
                    else:
                        clean_cols.append(c)
            idx_entry: dict[str, Any] = {
                "table": table_name,
                "name": idx_name,
                "columns": clean_cols,
                "unique": bool(idx.get("unique", False)),
            }
            if expr:
                idx_entry["expression"] = expr
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

            if database_type == "postgresql" and idx_name:
                try:
                    _pg_c = engine.connect() if own_engine and engine is not None else connection
                    sort_rows = _pg_c.execute(
                        text("""
                            SELECT a.attname,
                                   pg_index_column_has_property(i.indexrelid, k, 'asc') AS is_asc,
                                   pg_index_column_has_property(i.indexrelid, k, 'nulls_first') AS nf
                            FROM pg_index i
                            CROSS JOIN LATERAL generate_series(0, i.indnkeyatts - 1) AS k
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

            if database_type == "postgresql" and idx_name:
                try:
                    _pg_c = engine.connect() if own_engine and engine is not None else connection
                    opclass_rows = _pg_c.execute(
                        text("""
                            SELECT a.attname, o.opcname
                            FROM pg_index i
                            CROSS JOIN LATERAL generate_series(0, i.indnkeyatts - 1) AS k
                            JOIN pg_class ci ON ci.oid = i.indexrelid
                            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = i.indkey[k]
                            JOIN pg_opclass o ON o.oid = i.indclass[k]
                            WHERE ci.relname = :idxname AND i.indkey[k] <> 0
                              AND COALESCE(o.opcdefault, false) = false
                            ORDER BY k
                        """),
                        {"idxname": idx_name},
                    ).fetchall()
                    if opclass_rows:
                        idx_entry["postgresql_ops"] = {r.attname: r.opcname for r in opclass_rows}
                except Exception:
                    pass

            if database_type == "postgresql" and idx_name:
                try:
                    _pg_c = engine.connect() if own_engine and engine is not None else connection
                    row = _pg_c.execute(
                        text("""
                            SELECT d.description
                            FROM pg_index i
                            JOIN pg_class ci ON ci.oid = i.indexrelid
                            LEFT JOIN pg_description d ON d.objoid = ci.oid AND d.objsubid = 0
                                WHERE ci.relname = :idxname
                        """),
                        {"idxname": idx_name},
                    ).scalar()
                    if row:
                        idx_entry["comment"] = row
                except Exception:
                    pass

            indexes[f"{table_name}.{idx_name}"] = idx_entry

        for fk in inspector.get_foreign_keys(table_name, **inspect_kw):
            fk_name = fk.get("name", "")
            if not fk_name:
                fk_name = f"fk_{table_name}_{'_'.join(fk.get('constrained_columns', []))}"
            fk_options = fk.get("options", {})
            fk_match = fk_options.get("match")
            if fk_match and fk_match.upper() != "SIMPLE":
                fk_match = fk_match.upper()
            else:
                fk_match = None
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
            if fk_match:
                constraints[f"{table_name}.{fk_name}"]["match"] = fk_match

        for uq in inspector.get_unique_constraints(table_name, **inspect_kw):
            uq_name = uq.get("name", "")
            if not uq_name:
                continue
            constraints[f"{table_name}.{uq_name}"] = {
                "type": "unique",
                "name": uq_name,
                "table": table_name,
                "columns": list(uq.get("column_names", [])),
            }

        for ck in inspector.get_check_constraints(table_name, **inspect_kw):
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
            _regclass_name = f"{pg_schema}.{table_name}" if pg_schema else table_name
            try:
                no_inherit_rows = _pg_conn.execute(
                    text("SELECT conname, connoinherit FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'c'"),
                    {"t": _regclass_name},
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
                    {"t": _regclass_name},
                ).fetchall()
                for r in defer_rows:
                    cname = f"{table_name}.{r[0]}"
                    if cname in constraints:
                        constraints[cname]["deferrable"] = bool(r[1])
                        constraints[cname]["initially_deferred"] = bool(r[2])
            except Exception:
                pass
            try:
                validated_rows = _pg_conn.execute(
                    text("SELECT conname, contype, convalidated FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype IN ('f', 'c')"),
                    {"t": _regclass_name},
                ).fetchall()
                for r in validated_rows:
                    cname = f"{table_name}.{r[0]}"
                    if cname in constraints:
                        constraints[cname]["validated"] = bool(r[2])
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

        try:
            _pg_conn = engine.connect() if own_engine else connection
            domain_rows = _pg_conn.execute(
                text("""
                    SELECT t.typname AS domain_name,
                           pg_catalog.format_type(t.typbasetype, t.typtypmod) AS domain_type,
                           t.typnotnull AS not_null,
                           pg_catalog.pg_get_expr(t.typdefaultbin, 'pg_catalog.pg_class'::regclass) AS default,
                           n.nspname AS schema
                    FROM pg_catalog.pg_type t
                    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                    WHERE t.typtype = 'd'
                      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY t.typname
                """),
            ).fetchall()
            for r in domain_rows:
                domain_info = {
                    "domain_type": r.domain_type,
                    "not_null": bool(r.not_null),
                }
                if r.default:
                    domain_info["default"] = r.default
                domains[r.domain_name] = domain_info
                if r.schema and r.schema != "public":
                    domains[r.domain_name]["schema"] = r.schema
            # Also extract domain check constraints
            check_rows = _pg_conn.execute(
                text("""
                    SELECT t.typname AS domain_name,
                           pg_catalog.pg_get_constraintdef(c.oid) AS check_def
                    FROM pg_catalog.pg_type t
                    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                    JOIN pg_catalog.pg_constraint c ON c.contypid = t.oid AND c.contype = 'c'
                    WHERE t.typtype = 'd'
                      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                """),
            ).fetchall()
            for r in check_rows:
                if r.domain_name in domains:
                    domains[r.domain_name]["check"] = r.check_def
            if own_engine:
                _pg_conn.close()
        except Exception:
            pass

        try:
            view_names = inspector.get_view_names(**inspect_kw)
            _pg_conn = engine.connect() if own_engine else connection
            for view_name in view_names:
                if view_name in tables:
                    continue
                view_columns = inspector.get_columns(view_name, **inspect_kw)
                view_pk = inspector.get_pk_constraint(view_name, **inspect_kw)
                view_pk_columns = set(view_pk.get("constrained_columns", []) or [])

                view_columns_dict: dict[str, Any] = {}
                for col in view_columns:
                    col_name = col["name"]
                    col_type = col.get("type", "")
                    normalized = normalize_type(str(col_type))
                    view_columns_dict[col_name] = {
                        "type": normalized["type"],
                        "nullable": bool(col.get("nullable", True)),
                        "primary_key": col_name in view_pk_columns,
                        "default": col.get("default"),
                        "autoincrement": _is_autoincrement(col),
                    }
                    if normalized.get("raw"):
                        view_columns_dict[col_name]["raw"] = True
                    if "length" in normalized:
                        view_columns_dict[col_name]["length"] = normalized["length"]
                    if "precision" in normalized:
                        view_columns_dict[col_name]["precision"] = normalized["precision"]
                    if "scale" in normalized:
                        view_columns_dict[col_name]["scale"] = normalized["scale"]
                    comment = col.get("comment")
                    if comment is not None:
                        view_columns_dict[col_name]["comment"] = comment

                view_definition = None
                view_materialized = False
                try:
                    vrow = _pg_conn.execute(
                        text("SELECT pg_get_viewdef(:t, false) AS vdef, relkind FROM pg_class WHERE oid = CAST(:t2 AS regclass)"),
                        {"t": view_name, "t2": view_name},
                    ).fetchone()
                    if vrow:
                        view_definition = vrow[0] if vrow[0] else None
                        view_materialized = vrow[1] == 'm'
                except Exception:
                    pass

                view_entry: dict[str, Any] = {
                    "columns": view_columns_dict,
                    "primary_key": list(view_pk_columns) if view_pk_columns else [],
                    "comment": None,
                    "schema": pg_schema,
                    "object_type": "view",
                    "pg_view_definition": view_definition,
                    "pg_view_materialized": view_materialized,
                }
                try:
                    view_comment = inspector.get_table_comment(view_name, **inspect_kw)
                    if view_comment and view_comment.get("text"):
                        view_entry["comment"] = view_comment["text"]
                except Exception:
                    pass

                tables[view_name] = view_entry

            # Extract materialized views — invisible to both get_table_names() and get_view_names()
            try:
                matview_q = "SELECT relname FROM pg_class WHERE relkind = 'm'"
                if pg_schema:
                    matview_q += " AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = :schema)"
                    matview_rows = _pg_conn.execute(text(matview_q), {"schema": pg_schema})
                else:
                    matview_rows = _pg_conn.execute(text(matview_q + " AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())"))
                for mrow in matview_rows:
                    mv_name = mrow[0]
                    if mv_name in tables:
                        # Convert existing table entry to materialized view entry
                        mv_entry = tables[mv_name]
                        try:
                            vdef_row = _pg_conn.execute(
                                text("SELECT pg_get_viewdef(:t, false)"),
                                {"t": mv_name},
                            ).fetchone()
                            mv_entry["pg_view_definition"] = vdef_row[0] if vdef_row else None
                        except Exception:
                            mv_entry["pg_view_definition"] = None
                        mv_entry["pg_view_materialized"] = True
                        mv_entry["object_type"] = "materialized_view"
                        mv_entry["schema"] = pg_schema
                        mv_entry.pop("options", None)
                        mv_entry.pop("foreign_keys", None)
                    else:
                        # Extract from scratch (matview not returned by get_table_names)
                        try:
                            mv_columns = inspector.get_columns(mv_name, **inspect_kw)
                            mv_pk = inspector.get_pk_constraint(mv_name, **inspect_kw)
                            mv_pk_cols = set(mv_pk.get("constrained_columns", []) or [])
                            mv_cols_dict = {}
                            for col in mv_columns:
                                cname = col["name"]
                                ctype = col.get("type", "")
                                norm = normalize_type(str(ctype))
                                mv_cols_dict[cname] = {
                                    "type": norm["type"],
                                    "nullable": bool(col.get("nullable", True)),
                                    "primary_key": cname in mv_pk_cols,
                                    "default": col.get("default"),
                                    "autoincrement": _is_autoincrement(col),
                                }
                            vdef_row = _pg_conn.execute(
                                text("SELECT pg_get_viewdef(:t, false)"),
                                {"t": mv_name},
                            ).fetchone()
                            vdef = vdef_row[0] if vdef_row else None
                            tables[mv_name] = {
                                "columns": mv_cols_dict,
                                "primary_key": list(mv_pk_cols) if mv_pk_cols else [],
                                "comment": None,
                                "schema": pg_schema,
                                "object_type": "materialized_view",
                                "pg_view_definition": vdef,
                                "pg_view_materialized": True,
                            }
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                seq_rows = _pg_conn.execute(
                    text("""SELECT seq.relname AS seq_name,
                                   s.seqincrement, s.seqmin, s.seqmax, s.seqstart,
                                   s.seqcycle, pg_get_userbyid(seq.relowner) AS owned_by
                            FROM pg_sequence s
                            JOIN pg_class seq ON seq.oid = s.seqrelid
                            WHERE seq.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = current_schema())"""),
                ).fetchall()
                for r in seq_rows:
                    seq_info: dict[str, Any] = {"increment": r.seqincrement}
                    if r.seqmin is not None:
                        seq_info["minvalue"] = r.seqmin
                    if r.seqmax is not None:
                        seq_info["maxvalue"] = r.seqmax
                    if r.seqstart is not None:
                        seq_info["start"] = r.seqstart
                    if r.seqcycle:
                        seq_info["cycle"] = True
                    if r.owned_by:
                        seq_info["owned_by"] = r.owned_by
                    sequences[r.seq_name] = seq_info
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('sequences extraction failed: %s', e)

            try:
                comp_rows = _pg_conn.execute(
                    text("""SELECT t.typname AS type_name, n.nspname AS schema,
                                   a.attname AS col_name,
                                   pg_catalog.format_type(a.atttypid, a.atttypmod) AS col_type
                            FROM pg_catalog.pg_type t
                            JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                            JOIN pg_catalog.pg_attribute a ON a.attrelid = t.typrelid
                            WHERE t.typtype = 'c'
                              AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                              AND NOT EXISTS (
                                  SELECT 1 FROM pg_class c
                                  WHERE c.relname = t.typname
                                    AND c.relnamespace = t.typnamespace
                                    AND c.relkind IN ('r', 'v', 'm', 'S', 't', 'p'))
                              AND a.attnum > 0 AND NOT a.attisdropped
                            ORDER BY t.typname, a.attnum"""),
                ).fetchall()
                comp_type_map: dict[str, dict[str, Any]] = {}
                for r in comp_rows:
                    tname = r.type_name
                    if tname not in comp_type_map:
                        comp_type_map[tname] = {"columns": []}
                        if r.schema and r.schema != "public":
                            comp_type_map[tname]["schema"] = r.schema
                    comp_type_map[tname]["columns"].append({"name": r.col_name, "type": r.col_type})
                composite_types.update(comp_type_map)
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('composite_types extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                func_rows = _pg_conn.execute(
                    text("""SELECT n.nspname AS schema, p.proname AS func_name,
                                   pg_catalog.pg_get_functiondef(p.oid) AS definition
                            FROM pg_catalog.pg_proc p
                            JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
                            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                              AND p.prokind IN ('f', 'p', 'w')
                            ORDER BY p.proname"""),
                ).fetchall()
                for r in func_rows:
                    func_entry: dict[str, Any] = {"definition": r.definition}
                    if r.schema and r.schema != "public":
                        func_entry["schema"] = r.schema
                    functions[r.func_name] = func_entry
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('functions extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                role_rows = _pg_conn.execute(
                    text("""SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb,
                                   rolcanlogin, rolconnlimit, rolvaliduntil
                            FROM pg_roles WHERE rolname NOT LIKE 'pg_%'"""),
                ).fetchall()
                for r in role_rows:
                    role_info: dict[str, Any] = {}
                    if r.rolsuper:
                        role_info["superuser"] = True
                    if not r.rolinherit:
                        role_info["inherit"] = False
                    if r.rolcreaterole:
                        role_info["createrole"] = True
                    if r.rolcreatedb:
                        role_info["createdb"] = True
                    if r.rolcanlogin:
                        role_info["login"] = True
                    if r.rolconnlimit is not None and r.rolconnlimit != -1:
                        role_info["connlimit"] = r.rolconnlimit
                    if r.rolvaliduntil:
                        role_info["valid_until"] = str(r.rolvaliduntil)
                    roles[r.rolname] = role_info
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('roles extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                dp_rows = _pg_conn.execute(
                    text("""SELECT n.nspname, COALESCE(r.rolname, 'PUBLIC') AS grantee,
                                   da.defaclobjtype, acl.privilege_type
                            FROM pg_default_acl da
                            JOIN pg_namespace n ON n.oid = da.defaclnamespace
                            CROSS JOIN LATERAL aclexplode(da.defaclacl) AS acl
                            LEFT JOIN pg_roles r ON r.oid = acl.grantee"""),
                ).fetchall()
                dp_map: dict[str, dict[str, Any]] = {}
                for r in dp_rows:
                    obj_type_map = {'r': 'tables', 'S': 'sequences', 'f': 'functions', 'T': 'types', 'n': 'schemas'}
                    obj_type = obj_type_map.get(r.defaclobjtype, r.defaclobjtype)
                    key = f"{r.nspname}.{r.grantee}.{obj_type}"
                    if key not in dp_map:
                        dp_map[key] = {"schema": r.nspname, "role": r.grantee, "object_type": obj_type, "privileges": []}
                    dp_map[key]["privileges"].append(r.privilege_type)
                for val in dp_map.values():
                    val["privileges"] = list(sorted(set(val["privileges"])))
                default_privileges.update(dp_map)
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('default_privileges extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                sg_rows = _pg_conn.execute(
                    text("""SELECT n.nspname AS schema, COALESCE(r.rolname, 'PUBLIC') AS grantee,
                                   array_agg(acl.privilege_type ORDER BY acl.privilege_type) AS privileges,
                                   bool_or(acl.is_grantable) AS grantable
                            FROM pg_namespace n
                            CROSS JOIN LATERAL aclexplode(n.nspacl) AS acl
                            LEFT JOIN pg_roles r ON r.oid = acl.grantee
                            WHERE n.nspacl IS NOT NULL
                              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                            GROUP BY n.nspname, COALESCE(r.rolname, 'PUBLIC')"""),
                ).fetchall()
                sg_map: dict[str, list[dict[str, Any]]] = {}
                for r in sg_rows:
                    schema_name = r.schema
                    if schema_name not in sg_map:
                        sg_map[schema_name] = []
                    sg_map[schema_name].append({
                        "role": r.grantee,
                        "privileges": list(r.privileges) if r.privileges else ["ALL"],
                        "grantable": bool(r.grantable),
                    })
                schema_grants.update(sg_map)
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('schema_grants extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                et_rows = _pg_conn.execute(
                    text("""SELECT evtname, evtevent, proname AS func_name,
                                   n.nspname AS func_schema, evtenabled, evttags
                            FROM pg_event_trigger et
                            LEFT JOIN pg_proc p ON p.oid = et.evtfoid
                            LEFT JOIN pg_namespace n ON n.oid = p.pronamespace"""),
                ).fetchall()
                for r in et_rows:
                    et_entry: dict[str, Any] = {
                        "event": r.evtevent,
                        "function": {"name": r.func_name, "schema": r.func_schema},
                    }
                    if r.evttags:
                        et_entry["tags"] = list(r.evttags)
                    if r.evtenabled and r.evtenabled != 'O':
                        et_entry["enabled"] = r.evtenabled
                    event_triggers[r.evtname] = et_entry
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('event_triggers extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            try:
                if pg_version and pg_version >= (14, 0):
                    stats_rows = _pg_conn.execute(
                        text("""SELECT s.stxname,
                                       s.stxnamespace::regnamespace::text AS schema,
                                       c.relname AS table_name,
                                       s.stxkind AS kinds, s.stxkeys AS columns,
                                       pg_get_statisticsobjdef_expressions(s.oid) AS expressions
                                FROM pg_statistic_ext s
                                JOIN pg_class c ON c.oid = s.stxrelid
                                WHERE s.stxrelid > 0"""),
                    ).fetchall()
                else:
                    stats_rows = _pg_conn.execute(
                        text("""SELECT s.stxname,
                                       s.stxnamespace::regnamespace::text AS schema,
                                       c.relname AS table_name,
                                       s.stxkind AS kinds, s.stxkeys AS columns,
                                       NULL AS expressions
                                FROM pg_statistic_ext s
                                JOIN pg_class c ON c.oid = s.stxrelid
                                WHERE s.stxrelid > 0"""),
                    ).fetchall()
                for r in stats_rows:
                    stat_entry: dict[str, Any] = {"table": r.table_name, "kinds": list(r.kinds) if r.kinds else []}
                    if r.schema and r.schema != "public":
                        stat_entry["schema"] = r.schema
                    if r.columns:
                        stat_entry["columns"] = r.columns
                    if r.expressions:
                        exprs = [e.strip() for e in str(r.expressions).split(",") if e.strip()]
                        stat_entry["expressions"] = exprs
                    stat_key = f"{r.schema}.{r.stxname}" if r.schema and r.schema != "public" else r.stxname
                    extended_stats[stat_key] = stat_entry
            except Exception as e:
                import logging
                logging.getLogger('dbwarden.snapshot').warning('extended_stats extraction failed: %s', e)
                try:
                    _pg_conn.rollback()
                except Exception:
                    pass

            if own_engine:
                _pg_conn.close()
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
        "domains": domains,
        "indexes": indexes,
        "constraints": constraints,
        "sequences": sequences,
        "composite_types": composite_types,
        "functions": functions,
        "roles": roles,
        "default_privileges": default_privileges,
        "schema_grants": schema_grants,
        "event_triggers": event_triggers,
        "extended_stats": extended_stats,
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
    candidates: list[tuple[str, float, str]] = []

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
            path = os.path.join(schemas_dir, fname)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = 0.0
            candidates.append((version, mtime, path))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]))
    latest_path = candidates[-1][2]
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


def _normalize_index_col(col: str) -> str:
    """Normalize an index column/expression for stable comparison.

    Strips PostgreSQL type casts (::typename) that the canonical form
    returned by ``pg_get_indexdef`` may add (e.g. ``lower(email::text)``
    versus the user-written ``lower(email)``).
    """
    import re
    col = re.sub(r'::\w+(\.\w+)*(\[\])?', '', col)
    col = ' '.join(col.split())
    return col


def _index_sig(idx_or_info: dict | IndexInfo) -> tuple:
    if isinstance(idx_or_info, IndexInfo):
        return (
            tuple(_normalize_index_col(c) for c in idx_or_info.columns),
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
            tuple(sorted((idx_or_info.postgresql_ops or {}).items())),
            idx_or_info.comment,
            _normalize_index_col(idx_or_info.expression) if idx_or_info.expression else None,
        )
    return (
        tuple(_normalize_index_col(c) for c in idx_or_info.get("columns", [])),
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
        tuple(sorted((idx_or_info.get("postgresql_ops") or {}).items())),
        idx_or_info.get("comment"),
        _normalize_index_col(idx_or_info.get("expression")) if idx_or_info.get("expression") else None,
    )


def _index_op_from_info(info: IndexInfo, table: str) -> dict[str, Any]:
    op: dict[str, Any] = {
        "type": "add_index",
        "table": table,
        "columns": info.columns,
        "unique": info.unique,
    }
    if info.name is not None:
        op["index_name"] = info.name
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
    if info.postgresql_ops is not None:
        op["postgresql_ops"] = info.postgresql_ops
    if info.comment is not None:
        op["comment"] = info.comment
    if not info.concurrently:
        op["concurrently"] = False
    if info.clickhouse_type is not None:
        op["clickhouse_type"] = info.clickhouse_type
    if info.clickhouse_granularity is not None:
        op["clickhouse_granularity"] = info.clickhouse_granularity
    if info.expression is not None:
        op["expression"] = info.expression
    return op


def _build_create_table_sequence(table: ModelTable, db_name: str | None) -> list[MigrationStatement]:
    from dbwarden.engine.model_discovery import generate_create_table_sql, generate_drop_object_sql

    backend = _get_backend(db_name)
    order = StatementOrder.CREATE_VIEW if table.object_type in ("view", "materialized_view") else StatementOrder.CREATE_TABLE
    statements: list[MigrationStatement] = [
        MigrationStatement(
            order=order,
            upgrade_sql=generate_create_table_sql(table, db_name),
            rollback_sql=generate_drop_object_sql(table),
        )
    ]

    for idx in table.indexes:
        statements.extend(_build_index_sql(_index_op_from_info(idx, table.name), backend))

    return statements


def _join_creation_sql(table: ModelTable, db_name: str | None) -> str:
    return "\n\n".join(stmt.upgrade_sql for stmt in _build_create_table_sequence(table, db_name))



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
            continue
        if table.object_type == "view":
            continue

        snap_table = snapshot_tables[table.name]
        snap_columns = snap_table.get("columns", {})
        model_columns = {c.name: c for c in table.columns}

        # --- PG table metadata & exclude constraints via RegistryDriver ---

        # --- Phase 5: PG sub-object diff via RegistryDriver ---
        # Replaced inline storage_params, RLS, policies, grants.

    # --- Constraint diff via RegistryDriver ---
    from dbwarden.engine.pg_registry import ConstraintHandler, Op, RegistryDriver
    _con_handler = ConstraintHandler()
    _con_handler._snapshot = snapshot
    _con_handler._view_tables = {t.name for t in model_tables if getattr(t, 'object_type', None) == 'view'}
    _con_driver = RegistryDriver()
    _con_driver.register(_con_handler)
    _con_up, _con_rb = _con_driver.run(snapshot, model_tables, None)
    for op in _con_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _con_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- Column diff via RegistryDriver ---
    from dbwarden.engine.pg_registry import ColumnHandler, Op, RegistryDriver
    _col_handler = ColumnHandler()
    _col_handler._db_name = db_name
    _col_driver = RegistryDriver()
    _col_driver.register(_col_handler)
    _col_up, _col_rb = _col_driver.run(snapshot, model_tables, None)
    for op in _col_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _col_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- CH table metadata & recreate via RegistryDriver ---
    from dbwarden.engine.pg_registry import ChTableHandler, Op, RegistryDriver
    _ch_handler = ChTableHandler()
    _ch_handler.clickhouse_engine_recreate = clickhouse_engine_recreate
    _ch_driver = RegistryDriver()
    _ch_driver.register(_ch_handler)
    _ch_up, _ch_rb = _ch_driver.run(snapshot, model_tables, None)
    for op in _ch_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _ch_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- PG table metadata & exclude constraints via RegistryDriver ---
    from dbwarden.engine.pg_registry import PgTableHandler, Op, RegistryDriver
    _pgt_driver = RegistryDriver()
    _pgt_driver.register(PgTableHandler())
    _pgt_up, _pgt_rb = _pgt_driver.run(snapshot, model_tables, None)
    for op in _pgt_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pgt_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- Index diff via RegistryDriver ---
    from dbwarden.engine.pg_registry import IndexHandler, Op, RegistryDriver
    _idx_driver = RegistryDriver()
    _idx_driver.register(IndexHandler())
    _idx_up, _idx_rb = _idx_driver.run(snapshot, model_tables, None)
    for op in _idx_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _idx_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- Enum diff via RegistryDriver ---
    from dbwarden.engine.pg_registry import EnumHandler, Op, RegistryDriver
    _enum_driver = RegistryDriver()
    _enum_driver.register(EnumHandler())
    _enum_up_ops, _enum_rb_ops = _enum_driver.run(snapshot, model_tables, None)
    for op in _enum_up_ops:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _enum_rb_ops:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- PG preamble handlers (roles, sequences, composite types, etc.) ---
    from dbwarden.engine.pg_registry import (
        CompositeTypeHandler,
        DefaultPrivilegesHandler,
        EventTriggerHandler,
        ExtendedStatisticsHandler,
        FunctionHandler,
        PartitionHandler,
        RoleHandler,
        SequenceHandler,
        StatisticsHandler,
        TriggerHandler,
    )
    _pg_pre_driver = RegistryDriver()
    _pg_pre_driver.register(CompositeTypeHandler())
    _pg_pre_driver.register(DefaultPrivilegesHandler())
    _pg_pre_driver.register(EventTriggerHandler())
    _pg_pre_driver.register(ExtendedStatisticsHandler())
    _pg_pre_driver.register(FunctionHandler())
    _pg_pre_driver.register(PartitionHandler())
    _pg_pre_driver.register(RoleHandler())
    _pg_pre_driver.register(SequenceHandler())
    _pg_pre_driver.register(StatisticsHandler())
    _pg_pre_driver.register(TriggerHandler())
    _pg_pre_up, _pg_pre_rb = _pg_pre_driver.run(snapshot, model_tables, None)
    for op in _pg_pre_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pg_pre_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- Phase 5: PG sub-objects (storage params, RLS, policies, grants) ---
    from dbwarden.engine.pg_registry import (
        GrantsHandler,
        PoliciesHandler,
        StorageParamsHandler,
    )
    _pg5_driver = RegistryDriver()
    _pg5_driver.register(StorageParamsHandler())
    _pg5_driver.register(PoliciesHandler())
    _pg5_driver.register(GrantsHandler())
    _pg5_up, _pg5_rb = _pg5_driver.run(snapshot, model_tables, None)
    for op in _pg5_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _pg5_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- View diff via RegistryDriver ---
    from dbwarden.engine.pg_registry import ViewHandler
    _view_driver = RegistryDriver()
    _view_driver.register(ViewHandler())
    _view_up, _view_rb = _view_driver.run(snapshot, model_tables, None)
    for op in _view_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _view_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- Table create/drop/comment via RegistryDriver ---
    from dbwarden.engine.pg_registry import TableHandler
    _table_driver = RegistryDriver()
    _table_driver.register(TableHandler())
    _table_up, _table_rb = _table_driver.run(snapshot, model_tables, None)
    for op in _table_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _table_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

    # --- MySQL table-level ops ---
    from dbwarden.engine.pg_registry import MyTableHandler
    _my_driver = RegistryDriver()
    _my_driver.register(MyTableHandler())
    _my_up, _my_rb = _my_driver.run(snapshot, model_tables, None)
    for op in _my_up:
        upgrade_ops.append({"type": op.object_type, **op.upgrade_attrs})
    for op in _my_rb:
        rollback_ops.append({"type": op.object_type, **op.upgrade_attrs})

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
        allowed = {"recreate_ch_table", "drop_table", "create_table", "rename_table", "alter_enum_add_value", "create_type", "drop_type"}
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
        _qualified_name,
    )
    from dbwarden.engine.offline import reconstruct_model_table

    # Collect unique schemas from ops and emit CREATE SCHEMA IF NOT EXISTS
    schemas: set[str] = set()
    for op in upgrade_ops:
        if "schema" in op and op["schema"]:
            schemas.add(op["schema"])
    if schemas:
        ext_statements = "\n".join(
            f'CREATE SCHEMA IF NOT EXISTS "{s}";'
            for s in sorted(schemas)
        )
        upgrade_ops = [{"type": "create_schema", "schema": s, "sql": None} for s in sorted(schemas)] + upgrade_ops
        rollback_ops = rollback_ops + [{"type": "drop_schema", "schema": s, "sql": None} for s in reversed(sorted(schemas))]
    from dbwarden.engine.migration_name import Change
    from dbwarden.engine.pg_registry import (
        ChTableHandler,
        ColumnHandler,
        CompositeTypeHandler,
        ConstraintHandler,
        DefaultPrivilegesHandler,
        DomainHandler,
        EnumHandler,
        EventTriggerHandler,
        ExtendedStatisticsHandler,
        FunctionHandler,
        GrantsHandler,
        IndexHandler,
        MyTableHandler,
        Op,
        PartitionHandler,
        PgTableHandler,
        PoliciesHandler,
        RenameTableHandler,
        RoleHandler,
        SchemaHandler,
        SequenceHandler,
        StatisticsHandler,
        StorageParamsHandler,
        TableHandler,
        TriggerHandler,
        ViewHandler,
    )

    # Build emit dispatch: op_type -> handler instance
    _emit_dispatch: dict[str, Any] = {}
    for _h in (
        ChTableHandler(),
        ColumnHandler(),
        CompositeTypeHandler(),
        ConstraintHandler(),
        DefaultPrivilegesHandler(),
        DomainHandler(),
        EnumHandler(),
        EventTriggerHandler(),
        ExtendedStatisticsHandler(),
        FunctionHandler(),
        GrantsHandler(),
        IndexHandler(),
        MyTableHandler(),
        PartitionHandler(),
        PgTableHandler(),
        PoliciesHandler(),
        RenameTableHandler(),
        RoleHandler(),
        SchemaHandler(),
        SequenceHandler(),
        StatisticsHandler(),
        StorageParamsHandler(),
        TableHandler(),
        TriggerHandler(),
        ViewHandler(),
    ):
        for _ot in getattr(_h, "op_types", (_h.object_type,)):
            _emit_dispatch[_ot] = _h

    # Mapping from op_type to the dict key to use as Change.table
    _CHANGE_TABLE_KEY: dict[str, str] = {
        "rename_table": "old_table",
        "create_schema": "schema", "drop_schema": "schema",
        "create_domain": "name", "drop_domain": "name",
        "create_sequence": "name", "drop_sequence": "name",
        "alter_pg_storage_param": "table",
        "alter_pg_rls": "table",
        "add_policy": "table", "drop_policy": "table", "alter_policy": "table",
        "add_grant": "table", "revoke_grant": "table",
        "alter_enum_add_value": "enum_name", "create_type": "enum_name", "drop_type": "enum_name",
        "alter_my_table": "table",
        "alter_view": "table",
        "refresh_matview": "table",
        "create_table": "table",
        "drop_table": "table",
        "alter_table_comment": "table",
        "add_index": "table",
        "drop_index": "table",
        "alter_pg_table": "table",
        "add_exclude_constraint": "table",
        "drop_exclude_constraint": "table",
        "add_unique_constraint": "table",
        "drop_unique_constraint": "table",
        "rename_unique_constraint": "table",
        "add_check_constraint": "table",
        "drop_check_constraint": "table",
        "add_foreign_key": "table",
        "drop_foreign_key": "table",
        "alter_ch_options": "table",
        "recreate_ch_table": "table",
        "add_column": "table",
        "drop_column": "table",
        "rename_column": "table",
        "alter_column_type": "table",
        "alter_column_nullable": "table",
        "alter_column_autoincrement": "table",
        "alter_column_default": "table",
        "alter_column_comment": "table",
        "alter_ch_column": "table",
        "alter_pg_column_meta": "table",
        "alter_my_column_meta": "table",
        "create_composite_type": "type_name", "drop_composite_type": "type_name",
        "create_event_trigger": "trigger_name", "drop_event_trigger": "trigger_name",
        "create_extended_statistics": "stat_name", "drop_extended_statistics": "stat_name",
        "create_function": "function_name", "drop_function": "function_name",
        "create_role": "role_name", "drop_role": "role_name", "alter_role": "role_name",
        "alter_default_privileges": "schema",
    }
    # Optional second key for Change.target (only when present in the op dict)
    _CHANGE_TARGET_KEY: dict[str, str] = {
        "rename_table": "new_table",
        "alter_pg_storage_param": "param",
        "add_policy": "name", "drop_policy": "name", "alter_policy": "name",
        "add_grant": "role", "revoke_grant": "role",
        "alter_enum_add_value": "value",
        "alter_my_table": "key",
        "alter_pg_table": "key",
        "add_index": "columns",
        "add_column": "column",
        "drop_column": "column",
        "alter_column_type": "column",
        "alter_column_nullable": "column",
        "alter_column_autoincrement": "column",
        "alter_column_default": "column",
        "alter_column_comment": "column",
        "alter_ch_column": "column",
        "alter_pg_column_meta": "column",
        "alter_my_column_meta": "column",
        "attach_partition": "partition_name", "detach_partition": "partition_name",
        "alter_trigger": "name",
        "alter_column_statistics": "column",
    }

    statements: list[MigrationStatement] = []
    changes: list[Change] = []

    # Apply global concurrent flag to all index ops
    if not concurrent:
        for op in upgrade_ops:
            if op["type"] in ("add_index", "drop_index"):
                op["concurrently"] = False
        for op in rollback_ops:
            if op["type"] in ("add_index", "drop_index"):
                op["concurrently"] = False

    for op in upgrade_ops:
        # --- Dispatch to handler emit if a handler claims this op type ---
        _handler = _emit_dispatch.get(op["type"])
        if _handler is not None:
            _ot = op["type"]
            _attrs: dict[str, Any] = {k: v for k, v in op.items() if k != "type"}
            if _ot in ("create_domain", "drop_domain"):
                _info: dict[str, Any] = {"type": op.get("domain_type", "text")}
                for _k in ("schema", "default", "not_null", "check"):
                    if op.get(_k) is not None:
                        _info[_k] = op[_k]
                _attrs = {"domain_name": op.get("name") or op.get("domain_name", ""), "domain_info": _info}
            elif _ot in ("create_sequence", "drop_sequence"):
                _info = {}
                for _k in ("increment", "minvalue", "maxvalue", "start", "cycle", "owned_by", "schema"):
                    if op.get(_k) is not None:
                        _info[_k] = op[_k]
                _attrs = {"seq_name": op.get("name") or op.get("seq_name", ""), "seq_info": _info}
            _op_obj = Op(object_type=_ot, upgrade_attrs=_attrs)
            statements.extend(_handler.emit(_op_obj, db_name=db_name))
            _table_key = _CHANGE_TABLE_KEY.get(_ot, "table")
            _table = op.get(_table_key) or op.get("name") or op.get("table", "")
            _change: dict[str, Any] = {"operation": _ot, "table": _table}
            _target_key = _CHANGE_TARGET_KEY.get(_ot)
            if _target_key and op.get(_target_key) is not None:
                _change["target"] = op[_target_key]
            changes.append(Change(**_change))
            # Special handling for add_index: columns is a list, needs join + index_type
            if _ot == "add_index":
                changes[-1] = Change(
                    operation="add_index", table=_table,
                    target=",".join(op.get("columns", [])),
                    index_type=op.get("using"),
                )
            # Special handling for rename_column: target is new_name, not column
            if _ot == "rename_column":
                changes[-1] = Change(
                    operation="rename_column", table=_table,
                    target=op.get("new_name", ""),
                    resolved_from=op.get("resolved_from"),
                )
            # Special handling for add_foreign_key: composite target
            if _ot == "add_foreign_key":
                changes[-1] = Change(
                    operation="add_foreign_key", table=_table,
                    target=f"{op.get('referenced_table', '')}({','.join(op.get('referenced_columns', []))})",
                )
            # Extra per-index changes for create_table
            if _ot == "create_table":
                _ct_table = _find_model_table(_table, db_name=db_name)
                if _ct_table and hasattr(_ct_table, 'indexes') and _ct_table.indexes:
                    for _idx in _ct_table.indexes:
                        changes.append(Change(
                            operation="add_index", table=_table,
                            target=",".join(_idx.columns), index_type=_idx.using,
                        ))
            # Special handling for rename_table: resolved_from
            if _ot == "rename_table":
                changes[-1] = Change(
                    operation="rename_table", table=_table,
                    target=op.get("new_table", ""),
                    resolved_from=op.get("resolved_from"),
                )
            continue


    upgrade_sql, rollback_sql = _assemble_migration(statements)
    return upgrade_sql, rollback_sql, changes


def _build_clickhouse_recreate_table_sql(op: dict[str, Any], db_name: str | None) -> list[MigrationStatement]:
    from dbwarden.engine.model_discovery import generate_drop_object_sql
    from dbwarden.engine.offline import reconstruct_model_table

    table_name = op["table"]
    from_table = reconstruct_model_table(op["from_table"])
    to_table = reconstruct_model_table(op["to_table"])

    # Dictionaries use DROP + CREATE instead of rename swap
    if from_table.object_type == "dictionary" or to_table.object_type == "dictionary":
        upgrade_sql = (
            f"{generate_drop_object_sql(from_table)};\n"
            f"{_join_creation_sql(to_table, db_name)};"
        )
        rollback_sql = (
            f"{generate_drop_object_sql(to_table)};\n"
            f"{_join_creation_sql(from_table, db_name)};"
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
            f"{_join_creation_sql(to_table, db_name)};"
        )
        rollback_sql = (
            f"{generate_drop_object_sql(to_table)};\n"
            f"{_join_creation_sql(from_table, db_name)};"
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
        _join_creation_sql(ModelTable(
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
    rollback_parts.append(_join_creation_sql(ModelTable(
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



def _build_index_name(table: str, columns: list[str], unique: bool, using: str | None = None, expression: str | None = None) -> str:
    prefix = "uq" if unique else "idx"
    if expression:
        cols = "expr"
    else:
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
    postgresql_ops = op.get("postgresql_ops")
    concurrently = op.get("concurrently", True)
    clickhouse_type = op.get("clickhouse_type")
    clickhouse_granularity = op.get("clickhouse_granularity")
    expression = op.get("expression")
    idx_name = op.get("index_name") or _build_index_name(table, columns, unique, using, expression)

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

        # Column list with operator classes and sort orders
        col_parts = []
        for col in columns:
            col_sql = col
            opclass = (postgresql_ops or {}).get(col, "")
            if opclass and using:
                col_sql += f" {opclass}"
            sorting = (column_sorting or {}).get(col, "")
            if sorting:
                col_sql += f" {sorting}"
            col_parts.append(col_sql)
        if expression:
            col_parts.append(expression)
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
        if backend == "postgresql" and concurrently:
            from dbwarden.engine.file_parser import DBWARDEN_AUTOCOMMIT_MARKER

            upgrade = f"{DBWARDEN_AUTOCOMMIT_MARKER}\n{upgrade}"
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
            opclass = (postgresql_ops or {}).get(col, "")
            if opclass and using:
                col_sql += f" {opclass}"
            sorting = (column_sorting or {}).get(col, "")
            if sorting:
                col_sql += f" {sorting}"
            col_parts_rb.append(col_sql)
        if expression:
            col_parts_rb.append(expression)
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
