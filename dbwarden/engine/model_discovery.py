import os
import re
import sys
from pathlib import Path
from types import ModuleType
from dataclasses import dataclass, field
from typing import Any, List, Optional, Type

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base

from dbwarden.config import get_database, is_strict_translation
from dbwarden.engine.sqlite_translation import (
    translate_default_to_sqlite,
    translate_type_to_sqlite,
)
from dbwarden.exceptions import DBWardenConfigError
from dbwarden.logging import get_logger
from dbwarden.models import SchemaDifference
from dbwarden.schema import (
    ProjectionSpec,
    apply_meta,
    read_meta,
)
from dbwarden.schema._base import attach_meta
from dbwarden.schema._meta_reader import (
    _build_dbwarden_meta,
    _collect_meta_chain,
    _get_backend_for_class,
    _merge_meta_class,
    _type_check_field_attrs,
    _write_column_info,
)

Base = declarative_base()


def _apply_meta_fast(cls: type) -> None:
    if getattr(cls, "__dbwarden_meta_applied__", False):
        return

    meta_chain = _collect_meta_chain(cls)
    if not meta_chain:
        return

    backend = _get_backend_for_class(cls)
    merged_table: dict[str, Any] = {}
    merged_fields: dict[str, dict[str, Any]] = {}

    for meta_cls in reversed(meta_chain):
        _merge_meta_class(meta_cls, merged_table, merged_fields, backend=backend)

    table_obj = getattr(cls, "__table__", None)
    if table_obj is not None:
        column_names = {c.name for c in table_obj.columns}
        for field_name, attrs in merged_fields.items():
            if field_name not in column_names:
                continue
            _type_check_field_attrs(field_name, attrs, cls)
            _write_column_info(table_obj.c[field_name], attrs)

    attach_meta(cls, _build_dbwarden_meta(merged_table))
    cls.__dbwarden_meta_applied__ = True

VALID_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _render_mysql_column_type(type_str: str, meta: dict[str, Any]) -> str:
    rendered = type_str
    if meta.get("my_unsigned") and "UNSIGNED" not in rendered.upper():
        rendered = f"{rendered} UNSIGNED"
    return rendered


def _append_mysql_column_attrs(sql: str, meta: dict[str, Any]) -> str:
    if meta.get("my_charset"):
        sql += f" CHARACTER SET {meta['my_charset']}"
    if meta.get("my_collate"):
        sql += f" COLLATE {meta['my_collate']}"
    if meta.get("my_on_update"):
        sql += f" ON UPDATE {meta['my_on_update']}"
    return sql


def _validate_identifier(name: str, field: str = "identifier") -> None:
    """Validate SQL identifier (table/column name)."""
    if not name or not VALID_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid {field}: '{name}'. "
            "Must start with letter/underscore, contain only alphanumeric and underscore."
        )


def _get_backend_name(db_name: str | None = None) -> str:
    """Get the database backend name from config."""
    try:
        config = get_database(db_name)
        return config.database_type
    except Exception:
        return "sqlite"


def _map_sqlalchemy_type_to_backend(
    type_str: str, is_primary_key: bool = False, db_name: str | None = None,
    autoincrement: bool | None = None,
    backend: str | None = None,
) -> str:
    """
    Map SQLAlchemy type strings to backend-specific types.

    Args:
        type_str: The SQLAlchemy type string (e.g., "INTEGER", "DATETIME", "VARCHAR(100)").
        is_primary_key: Whether this column is a primary key (for SERIAL/BIGSERIAL mapping).
        db_name: Database name for backend detection.
        autoincrement: Whether the column has autoincrement enabled.

    Returns:
        Backend-specific type string.
    """
    backend = backend or _get_backend_name(db_name)

    if backend == "postgresql":
        type_upper = type_str.upper()

        if autoincrement is not False and is_primary_key and type_upper == "INTEGER":
            return "SERIAL"
        if autoincrement is not False and is_primary_key and type_upper == "BIGINTEGER":
            return "BIGSERIAL"

        type_mapping = {
            "DATETIME": "TIMESTAMP",
            "DATETIME(6)": "TIMESTAMP(6)",
            "DATETIME WITH TIME ZONE": "TIMESTAMPTZ",
            "TIMESTAMP(6) WITHOUT TIME ZONE": "TIMESTAMP(6)",
            "BLOB": "BYTEA",
            "BYTEA": "BYTEA",
        }
        return type_mapping.get(type_str.upper(), type_str)

    if backend in ("mysql", "mariadb"):
        type_upper = type_str.upper()
        type_mapping = {
            "BOOLEAN": "TINYINT(1)",
            "SERIAL": "BIGINT UNSIGNED",
        }
        return type_mapping.get(type_upper, type_str)

    if backend == "sqlite":
        strict = is_strict_translation()
        translated, warning = translate_type_to_sqlite(type_str, strict=strict)
        if warning:
            get_logger().warning(warning)
        return translated

    return type_str


class ModelColumn:
    """Represents a column from a SQLAlchemy model."""

    def __init__(
        self,
        name: str,
        type: str,
        nullable: bool,
        primary_key: bool,
        unique: bool,
        default: Optional[str],
        foreign_key: Optional[str],
        codec: Optional[str] = None,
        comment: Optional[str] = None,
        pg_meta: Optional[dict[str, Any]] = None,
        ch_meta: Optional[dict[str, Any]] = None,
        my_meta: Optional[dict[str, Any]] = None,
        autoincrement: Optional[bool] = None,
    ):
        self.name = name
        self.type = type
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.default = default
        self.foreign_key = foreign_key
        self.codec = codec
        self.comment = comment
        self.pg_meta = pg_meta or {}
        self.ch_meta = ch_meta or {}
        self.my_meta = my_meta or {}
        self.autoincrement = autoincrement

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "unique": self.unique,
            "default": self.default,
            "foreign_key": self.foreign_key,
            "codec": self.codec,
            "comment": self.comment,
            "pg_meta": self.pg_meta,
            "autoincrement": self.autoincrement,
        }
        if self.ch_meta:
            d["ch_meta"] = self.ch_meta
        if self.my_meta:
            d["my_meta"] = self.my_meta
        return d


@dataclass
class IndexInfo:
    columns: list[str]
    name: str | None = None
    unique: bool = False
    using: str | None = None
    where: str | None = None
    include: list[str] | None = None
    with_params: dict[str, Any] | None = None
    tablespace: str | None = None
    nulls_not_distinct: bool = False
    column_sorting: dict[str, str] | None = None
    comment: str | None = None
    concurrently: bool = True
    clickhouse_type: str | None = None
    clickhouse_granularity: int | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "columns": self.columns,
            "unique": self.unique,
        }
        if self.name is not None:
            d["name"] = self.name
        if self.using is not None:
            d["using"] = self.using
        if self.where is not None:
            d["where"] = self.where
        if self.include is not None:
            d["include"] = self.include
        if self.with_params is not None:
            d["with_params"] = self.with_params
        if self.tablespace is not None:
            d["tablespace"] = self.tablespace
        if self.nulls_not_distinct:
            d["nulls_not_distinct"] = True
        if self.column_sorting is not None:
            d["column_sorting"] = self.column_sorting
        if self.comment is not None:
            d["comment"] = self.comment
        if not self.concurrently:
            d["concurrently"] = False
        if self.clickhouse_type is not None:
            d["clickhouse_type"] = self.clickhouse_type
        if self.clickhouse_granularity is not None:
            d["clickhouse_granularity"] = self.clickhouse_granularity
        return d

    @staticmethod
    def from_dict(d: dict) -> "IndexInfo":
        return IndexInfo(
            name=d.get("name"),
            columns=list(d.get("columns", [])),
            unique=bool(d.get("unique", False)),
            using=d.get("using"),
            where=d.get("where"),
            include=list(d.get("include", [])) if d.get("include") else None,
            with_params=dict(d.get("with_params", {})) if d.get("with_params") else None,
            tablespace=d.get("tablespace"),
            nulls_not_distinct=bool(d.get("nulls_not_distinct", False)),
            column_sorting=dict(d.get("column_sorting", {})) if d.get("column_sorting") else None,
            comment=d.get("comment"),
            concurrently=bool(d.get("concurrently", True)),
            clickhouse_type=d.get("clickhouse_type"),
            clickhouse_granularity=d.get("clickhouse_granularity"),
        )


class ModelTable:
    """Represents a table from a SQLAlchemy model."""

    def __init__(
        self,
        name: str,
        columns: List[ModelColumn],
        clickhouse_options: Optional[dict] = None,
        object_type: str = "table",
        foreign_keys: Optional[list[dict]] = None,
        indexes: Optional[list[dict | IndexInfo]] = None,
        comment: str | None = None,
        checks: Optional[list[dict[str, Any]]] = None,
        uniques: Optional[list[dict[str, Any]]] = None,
        excludes: Optional[list[dict[str, Any]]] = None,
        pg_table: Optional[dict[str, Any]] = None,
        my_table: Optional[dict[str, Any]] = None,
    ):
        self.name = name
        self.columns = columns
        self.clickhouse_options = clickhouse_options or {}
        self.object_type = object_type
        self.foreign_keys = foreign_keys or []
        self.indexes: list[IndexInfo] = [
            IndexInfo.from_dict(idx) if isinstance(idx, dict) else idx
            for idx in (indexes or [])
        ]
        self.comment = comment
        self.checks = checks or []
        self.uniques = uniques or []
        self.excludes = excludes or []
        self.pg_table = pg_table or {}
        self.my_table = my_table or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": [col.to_dict() for col in self.columns],
            "clickhouse_options": self.clickhouse_options,
            "object_type": self.object_type,
            "foreign_keys": self.foreign_keys,
            "indexes": [idx.to_dict() if isinstance(idx, IndexInfo) else idx for idx in self.indexes],
            "comment": self.comment,
            "checks": self.checks,
            "uniques": self.uniques,
            "excludes": self.excludes,
            "pg_table": self.pg_table,
            "my_table": self.my_table,
        }


def _extract_dialect_option(idx: Any, key: str, default: Any = None) -> Any:
    """Extract a dialect option from a SQLAlchemy Index object, checking all backends."""
    for prefix in ("postgresql", "mysql", "mariadb", "sqlite"):
        val = idx.dialect_options.get(prefix, {}).get(key)
        if val is not None:
            return val
    return default


def _extract_table_args_dict(model_class: type) -> dict:
    table_args = getattr(model_class, "__table_args__", None)
    if isinstance(table_args, dict):
        return table_args
    if isinstance(table_args, tuple) and table_args and isinstance(table_args[-1], dict):
        return table_args[-1]
    return {}


def _ch_options_from_meta(model_class: type) -> dict:
    from dbwarden.databases.clickhouse import ChTableSpec

    dw_meta = read_meta(model_class)
    if not dw_meta:
        return {}

    raw = dw_meta.backend_table
    if raw is None:
        return {}

    options: dict[str, Any] = {}

    if isinstance(raw, dict):
        # Legacy path: plain dict (backward compat for direct __table_args__ usage)
        for key in (
            "ch_engine", "ch_order_by", "ch_primary_key", "ch_partition_by",
            "ch_sample_by", "ch_ttl", "ch_object_type", "ch_select_statement",
            "ch_to_table", "ch_dictionary", "ch_dict_layout", "ch_dict_source",
            "ch_dict_lifetime", "ch_dict_primary_key", "ch_zookeeper_path",
            "ch_replica_name", "ch_settings",
        ):
            if key in raw:
                options[key] = raw[key]
        ch_projections = raw.get("ch_projections") or []
        options["ch_projections"] = [
            p.to_dict() if isinstance(p, ProjectionSpec) else p
            for p in ch_projections
        ]
        _validate_ch_options(options)
        return options

    if not isinstance(raw, ChTableSpec):
        return {}

    if raw.engine:
        options["ch_engine_raw"] = raw.engine
        options["ch_engine"] = _serialize_ch_engine(raw.engine)
    if raw.order_by is not None:
        options["ch_order_by"] = raw.order_by
    if raw.primary_key is not None:
        options["ch_primary_key"] = raw.primary_key
    if raw.partition_by is not None:
        options["ch_partition_by"] = raw.partition_by
    if raw.sample_by is not None:
        options["ch_sample_by"] = raw.sample_by
    if raw.ttl is not None:
        options["ch_ttl"] = raw.ttl
    if raw.settings is not None:
        options["ch_settings"] = raw.settings
    if raw.zookeeper_path is not None:
        options["ch_zookeeper_path"] = raw.zookeeper_path
    if raw.replica_name is not None:
        options["ch_replica_name"] = raw.replica_name
    if raw.object_type is not None:
        options["ch_object_type"] = raw.object_type
    if raw.select_statement is not None:
        options["ch_select_statement"] = raw.select_statement
    if raw.to_table is not None:
        options["ch_to_table"] = raw.to_table

    # Extra attrs not on ChTableSpec: stored in table_attrs
    attrs = dw_meta.table_attrs
    if attrs.get("ch_dictionary"):
        options["ch_dictionary"] = True
    for key in ("ch_dict_layout", "ch_dict_source", "ch_dict_lifetime", "ch_dict_primary_key"):
        if key in attrs:
            options[key] = attrs[key]
    projections = attrs.get("ch_projections") or []
    options["ch_projections"] = [
        p.to_dict() if isinstance(p, ProjectionSpec) else p
        for p in projections
    ]

    _validate_ch_options(options)
    return options


def _serialize_ch_engine(engine: Any) -> str | tuple | None:
    from dbwarden.schema.engine import ChEngineSpec
    if isinstance(engine, ChEngineSpec):
        args = [engine.name]
        if engine.zookeeper_path is not None:
            args.append(engine.zookeeper_path)
        if engine.replica_name is not None:
            args.append(engine.replica_name)
        args.extend(engine.args)
        return tuple(args)
    if isinstance(engine, (str, tuple, list)):
        return engine
    return None


def _validate_ch_options(options: dict) -> None:
    order_by = options.get("ch_order_by")
    primary_key = options.get("ch_primary_key")
    projections = options.get("ch_projections")
    settings = options.get("ch_settings")

    if order_by is not None and not isinstance(order_by, (str, list, tuple)):
        raise ValueError("ch_order_by must be a string or list/tuple of strings")
    if isinstance(order_by, (list, tuple)):
        if not order_by:
            raise ValueError("ch_order_by cannot be empty")
        if not all(isinstance(item, str) and item.strip() for item in order_by):
            raise ValueError("ch_order_by entries must be non-empty strings")

    if primary_key is not None and not isinstance(primary_key, (str, list, tuple)):
        raise ValueError("ch_primary_key must be a string or list/tuple of strings")
    if isinstance(primary_key, (list, tuple)):
        if not primary_key:
            raise ValueError("ch_primary_key cannot be empty")
        if not all(isinstance(item, str) and item.strip() for item in primary_key):
            raise ValueError("ch_primary_key entries must be non-empty strings")

    if isinstance(order_by, (list, tuple)) and primary_key:
        normalized = [item.strip() for item in order_by]
        if isinstance(primary_key, str):
            pk_parts = [primary_key]
        else:
            pk_parts = [item.strip() for item in primary_key]
        if normalized[:len(pk_parts)] != pk_parts:
            raise ValueError("ch_primary_key must be a prefix of ch_order_by")

    ttl = options.get("ch_ttl")
    if ttl is not None:
        if not isinstance(ttl, list):
            raise ValueError("ch_ttl must be a list of expressions")
        if not all(isinstance(item, str) and item.strip() for item in ttl):
            raise ValueError("ch_ttl entries must be non-empty strings")

    if projections is not None:
        if not isinstance(projections, list):
            raise ValueError("ch_projections must be a list")
        for proj in projections:
            if isinstance(proj, dict):
                if not proj.get("name"):
                    raise ValueError("ch_projections entries require name")
            elif not hasattr(proj, "name") or not hasattr(proj, "query"):
                raise ValueError("ch_projections entries must be ProjectionSpec or dict with name/query")

    if settings is not None:
        if not isinstance(settings, dict):
            raise ValueError("ch_settings must be a dict")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in settings.items()):
            raise ValueError("ch_settings keys and values must be strings")

    if options.get("ch_dictionary") or any(options.get(k) for k in ("ch_dict_layout", "ch_dict_source", "ch_dict_lifetime")):
        if not options.get("ch_dict_layout"):
            raise ValueError("ch_dict_layout is required for dictionary tables")
        if not options.get("ch_dict_source"):
            raise ValueError("ch_dict_source is required for dictionary tables")
        if not options.get("ch_dict_lifetime"):
            raise ValueError("ch_dict_lifetime is required for dictionary tables")

    zk = options.get("ch_zookeeper_path")
    if zk is not None and not isinstance(zk, str):
        raise ValueError("ch_zookeeper_path must be a string")
    replica = options.get("ch_replica_name")
    if replica is not None and not isinstance(replica, str):
        raise ValueError("ch_replica_name must be a string")


def _detect_ch_object_type(options: dict) -> str:
    explicit = options.get("ch_object_type")
    auto: str = "table"

    has_select = bool(options.get("ch_select_statement"))
    has_dict = bool(options.get("ch_dictionary"))
    has_dict_fields = any(
        options.get(k) for k in ("ch_dict_layout", "ch_dict_source", "ch_dict_lifetime", "ch_dict_primary_key")
    )

    if has_select:
        auto = "materialized_view"
    if has_dict or has_dict_fields:
        if auto == "materialized_view":
            raise DBWardenConfigError(
                "Conflicting ClickHouse object type: both ch_select_statement "
                "and dictionary fields (ch_dict_layout, etc.) are set"
            )
        auto = "dictionary"

    if explicit is not None:
        if explicit != auto and not (explicit == "table" and auto == "table"):
            raise DBWardenConfigError(
                f"Explicit ch_object_type={explicit!r} conflicts with "
                f"detected type {auto!r} based on other ch_* options"
            )
        return explicit

    return auto


def _render_clickhouse_projection(projection: dict | Any) -> str:
    if isinstance(projection, dict):
        return f"PROJECTION {projection['name']} ({projection['query']})"
    return f"PROJECTION {projection.name} ({projection.query})"


def _render_clickhouse_projections(table: ModelTable) -> list[str]:
    projections = table.clickhouse_options.get("ch_projections") or []
    return [_render_clickhouse_projection(projection) for projection in projections]


def _format_clickhouse_expression(value: str | list[str] | tuple[str, ...]) -> str:
    if isinstance(value, str):
        return value
    return "(" + ", ".join(value) + ")"


def _format_clickhouse_engine(value: str | tuple | list, zookeeper_path: str | None = None, replica_name: str | None = None) -> str:
    if isinstance(value, str):
        engine_name = value
        extra_args = []
    elif isinstance(value, (tuple, list)) and value:
        engine_name = value[0]
        if not isinstance(engine_name, str) or not engine_name.strip():
            raise ValueError("ch_engine must start with a non-empty engine name")
        extra_args = list(str(item) for item in value[1:])
    else:
        raise ValueError("ch_engine must be a string or tuple/list")

    if zookeeper_path is not None:
        extra_args.insert(0, zookeeper_path)
    if replica_name is not None:
        extra_args.insert(1 if zookeeper_path is not None else 0, replica_name)

    if extra_args:
        return f"{engine_name}({', '.join(extra_args)})"
    return f"{engine_name}()"


def _render_clickhouse_table_suffix(table: ModelTable) -> str:
    options = table.clickhouse_options
    if not options:
        return " ENGINE = MergeTree()"

    parts: list[str] = []

    engine_raw = options.get("ch_engine", "MergeTree")
    if isinstance(engine_raw, str):
        engine_name = engine_raw
        engine_args = []
    elif isinstance(engine_raw, tuple):
        engine_name = engine_raw[0] if engine_raw else "MergeTree"
        engine_args = list(str(a) for a in engine_raw[1:])
    elif isinstance(engine_raw, (list, tuple)):
        engine_name = engine_raw[0] if engine_raw else "MergeTree"
        engine_args = list(str(a) for a in engine_raw[1:])
    else:
        engine_name = "MergeTree"
        engine_args = []
    zk_path = options.get("ch_zookeeper_path")
    replica_name = options.get("ch_replica_name")
    if zk_path is not None:
        engine_args.insert(0, zk_path)
    if replica_name is not None:
        engine_args.insert(1 if zk_path is not None else 0, replica_name)
    if engine_args:
        parts.append(f"ENGINE = {engine_name}({', '.join(engine_args)})")
    else:
        parts.append(f"ENGINE = {engine_name}()")

    order_by = options.get("ch_order_by")
    if order_by is not None:
        parts.append(f"ORDER BY {_format_clickhouse_expression(order_by)}")

    primary_key = options.get("ch_primary_key")
    if primary_key:
        parts.append(f"PRIMARY KEY {_format_clickhouse_expression(primary_key)}")

    partition_by = options.get("ch_partition_by")
    if partition_by:
        parts.append(f"PARTITION BY {partition_by}")

    sample_by = options.get("ch_sample_by")
    if sample_by:
        parts.append(f"SAMPLE BY {sample_by}")

    ttl = options.get("ch_ttl")
    if ttl:
        parts.append("TTL " + ", ".join(ttl) if isinstance(ttl, list) else f"TTL {ttl}")

    settings = options.get("ch_settings")
    if settings:
        settings_str = ", ".join(f"{k}={v}" for k, v in settings.items())
        parts.append(f"SETTINGS {settings_str}")

    return "\n" + "\n".join(parts)


def _map_sa_type_to_clickhouse(column) -> str:
    raw_type_str = str(column.type).upper().strip()
    ch_type = _render_ch_type_from_sa(column.type, raw_type_str)

    ch_meta_attrs = getattr(column, "info", {})
    if ch_meta_attrs.get("ch_low_cardinality"):
        ch_type = f"LowCardinality({ch_type})"
    if ch_meta_attrs.get("ch_nullable"):
        ch_type = f"Nullable({ch_type})"

    return ch_type


def _render_ch_type_from_sa(sa_type, raw_type_str: str) -> str:
    item_type = getattr(sa_type, "item_type", None)
    if item_type is not None:
        inner = _render_ch_type_from_sa(item_type, str(item_type).upper().strip())
        return f"Array({inner})"

    enums = getattr(sa_type, "enums", None)
    if enums is not None and enums:
        count = len(enums)
        values = ", ".join(repr(v) for v in enums)
        if count <= 127:
            return f"Enum8({values})"
        return f"Enum16({values})"

    name = raw_type_str
    base = name.split("(")[0] if "(" in name else name

    if base in ("VARCHAR", "CHAR", "CHARACTER VARYING", "TEXT", "CLOB", "STRING"):
        return "String"
    if base in ("INT", "INTEGER", "INT32"):
        return "Int32"
    if base in ("BIGINT", "BIGINTEGER", "INT64"):
        return "Int64"
    if base in ("SMALLINT", "SMALLINTEGER", "INT16", "TINYINT"):
        return "Int16"
    if base in ("FLOAT", "FLOAT32", "REAL"):
        return _maybe_float32(sa_type)
    if base == "DOUBLE_PRECISION":
        return "Float64"
    if base in ("NUMERIC", "DECIMAL", "NUMBER"):
        return _map_numeric_to_decimal(name)
    if base == "BOOLEAN":
        return "Bool"
    if base == "DATE":
        return "Date"
    if base in ("DATETIME", "TIMESTAMP"):
        return _map_datetime(sa_type, name)
    if base in ("BLOB", "BYTEA", "BINARY", "LARGEBINARY"):
        return "String"
    if base == "JSON":
        return "JSON"
    if base in ("UUID",):
        return "UUID"
    if base in ("TIME", "INTERVAL"):
        return "String"

    return name


def _maybe_float32(sa_type) -> str:
    precision = getattr(sa_type, "precision", None)
    if precision is None:
        return "Float64"
    if precision <= 24:
        return "Float32"
    return "Float64"


def _map_numeric_to_decimal(name: str) -> str:
    import re
    m = re.match(r"NUMERIC\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)", name, re.IGNORECASE)
    if not m:
        m = re.match(r"DECIMAL\s*\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)", name, re.IGNORECASE)
    if m:
        p = m.group(1)
        s = m.group(2) or "0"
        return f"Decimal({p}, {s})"
    return "Decimal(38, 0)"


def _map_datetime(sa_type, name: str) -> str:
    import re
    m = re.match(r"DATETIME(?:64)?\s*\(\s*(\d+)\s*\)", name, re.IGNORECASE)
    if m:
        return f"DateTime64({m.group(1)})"
    timezone = getattr(sa_type, "timezone", None)
    if timezone:
        return "DateTime64(3)"
    return "DateTime"


def load_model_from_path(filepath: str) -> Optional[ModuleType]:
    """
    Load a SQLAlchemy model from a Python file path.

    Args:
        filepath: Path to the Python file containing SQLAlchemy models.

    Returns:
        The loaded module or None if failed.
    """
    from dbwarden.sandbox import load_model_module

    base_dir = Path.cwd().resolve()
    return load_model_module(Path(filepath), base_dir)


def discover_models_in_directory(directory: str) -> List[str]:
    """
    Discover model files in a directory.

    Args:
        directory: Path to search for model files.

    Returns:
        List of Python file paths that may contain models.
    """
    model_files = []
    directory_path = Path(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        return []

    for filepath in directory_path.rglob("*.py"):
        if filepath.name.startswith("_"):
            continue
        model_files.append(str(filepath))

    return model_files


def get_all_model_tables(
    model_paths: Optional[List[str]] = None,
    db_name: str | None = None,
) -> List[ModelTable]:
    """
    Extract table definitions from SQLAlchemy models.

    Args:
        model_paths: List of paths to model files. If None, auto-discovers in models/ directory.

    Returns:
        List of ModelTable objects representing all tables in the models.
    """
    tables = []
    seen_tables = set()

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    # Ensure project root is in sys.path for proper imports
    cwd = str(Path.cwd().resolve())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Also check parent directories for project roots
    for potential_root in [cwd, str(Path(cwd).parent)]:
        if potential_root not in sys.path:
            sys.path.insert(0, potential_root)

    for model_path in model_paths:
        if not os.path.exists(model_path):
            continue

        if os.path.isdir(model_path):
            model_files = discover_models_in_directory(model_path)
        else:
            model_files = [model_path]

        for model_file in model_files:
            module = load_model_from_path(model_file)
            if module is None:
                continue

            for attr in module.__dict__.values():
                if not isinstance(attr, type):
                    continue
                if getattr(attr, "__module__", None) != getattr(module, "__name__", None):
                    continue
                tablename = getattr(attr, "__tablename__", None)
                table_obj = getattr(attr, "__table__", None)
                if tablename is None or table_obj is None:
                    continue
                if tablename in seen_tables:
                    continue
                seen_tables.add(tablename)
                table = extract_table_from_model(attr, db_name=db_name)
                if table:
                    tables.append(table)

    return tables


def _find_project_root(start: Path) -> Path:
    PROJECT_ROOT_MARKERS = {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        ".git",
        ".hg",
        ".svn",
    }
    for candidate in [start] + list(start.parents):
        if any((candidate / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return candidate
    return start


def auto_discover_model_paths() -> List[str]:
    """
    Auto-discover model paths by looking for models/ or model/ directories.

    Searches:
    1. Current directory for models/ or model/
    2. All subdirectories for models/ or model/ folders
    3. Parent directories (up to the project root, detected via
       pyproject.toml, setup.py, .git, etc.)
    4. Ignores common lib folders (.venv, node_modules, __pycache__, etc.)

    Returns:
        List of directories that may contain models.
    """
    model_paths = []
    current = Path.cwd().resolve()
    project_root = _find_project_root(current)

    IGNORED_DIRS = {
        ".venv",
        "node_modules",
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        "build",
        "dist",
        "egg-info",
        ".tox",
        ".nox",
        "venv",
        "ENV",
        ".egg",
        ".cache",
        "coverage",
        ".pytest_cache",
        "site-packages",
        "Lib",
        "Scripts",
        "bin",
        "include",
    }

    def find_model_dirs_in(directory: Path) -> List[str]:
        """Find models/ or model/ folders inside a directory."""
        found = []
        try:
            if not directory.exists() or not directory.is_dir():
                return found

            for item in directory.iterdir():
                try:
                    if item.is_dir() and item.name not in IGNORED_DIRS:
                        for model_name in ["models", "model"]:
                            model_dir = item / model_name
                            if model_dir.exists() and model_dir.is_dir():
                                found.append(str(model_dir))
                except PermissionError:
                    continue
        except PermissionError:
            pass
        return found

    while True:
        # Check for models/ or model/ in current directory
        for dirname in ["models", "model"]:
            model_dir = current / dirname
            if model_dir.exists() and model_dir.is_dir():
                if str(model_dir) not in model_paths:
                    model_paths.append(str(model_dir))

        # Check all subdirectories for models/model folders
        for subdir in find_model_dirs_in(current):
            if subdir not in model_paths:
                model_paths.append(subdir)

        if current == project_root or current.parent == current:
            break
        current = current.parent

    return model_paths


def extract_table_from_model(
    model_class: type, db_name: str | None = None
) -> Optional[ModelTable]:
    """
    Extract table information from a SQLAlchemy model class.

    Args:
        model_class: SQLAlchemy model class.
        db_name: Database name for backend-specific type mapping.

    Returns:
        ModelTable object or None if extraction fails.
    """
    try:
        import os
        import time

        debug_timing = os.environ.get("DBWARDEN_DEBUG_TIMING")
        start = time.time()
        _apply_meta_fast(model_class)
        if debug_timing:
            print(f"TIMING {model_class.__name__} apply_meta {time.time() - start:.3f}s", flush=True)
            start = time.time()
        dw_meta = read_meta(model_class)
        if debug_timing:
            print(f"TIMING {model_class.__name__} read_meta {time.time() - start:.3f}s", flush=True)
            start = time.time()
        backend = _get_backend_name(db_name)
        table_name = model_class.__tablename__
        columns = []

        for column in model_class.__table__.columns:
            col = extract_column_info(column, db_name=db_name, backend=backend)
            if col:
                columns.append(col)
        if debug_timing:
            print(f"TIMING {model_class.__name__} columns {len(columns)} {time.time() - start:.3f}s", flush=True)
            start = time.time()

        # Extract FK info from parsed column.foreign_key strings
        foreign_keys: list[dict[str, Any]] = []
        for col in columns:
            if col.foreign_key:
                # Format: "referred_table(referred_column)"
                fk = col.foreign_key
                if "(" in fk and fk.endswith(")"):
                    ref_table, ref_col = fk[:-1].split("(", 1)
                else:
                    ref_table, ref_col = fk, "id"
                foreign_keys.append({
                    "columns": [col.name],
                    "referred_table": ref_table,
                    "referred_columns": [ref_col],
                })

        # Extract indexes from SQLAlchemy model
        indexes: list[IndexInfo] = []
        for idx in model_class.__table__.indexes:
            idx_cols = list(idx.columns.keys())
            info = IndexInfo(
                name=idx.name,
                columns=idx_cols,
                unique=bool(idx.unique),
                using=_extract_dialect_option(idx, "using"),
                where=_extract_dialect_option(idx, "where"),
                include=list(idx.include_columns) if hasattr(idx, "include_columns") and idx.include_columns else None,
                nulls_not_distinct=bool(_extract_dialect_option(idx, "nulls_not_distinct", False)),
                with_params=_extract_dialect_option(idx, "with"),
                tablespace=_extract_dialect_option(idx, "tablespace"),
            )
            # Extract per-column sort info from Index expressions
            for expr in idx.expressions:
                if hasattr(expr, "name") and expr.name:
                    # Determine ASC/DESC and NULLS FIRST/LAST from the expression
                    sorting_parts = []
                    order = getattr(expr, "_order", None)
                    if order is not None:
                        sorting_parts.append(order)
                    nulls = getattr(expr, "_nulls", None)
                    if nulls is not None:
                        sorting_parts.append(f"nulls {nulls}")
                    if sorting_parts:
                        if info.column_sorting is None:
                            info.column_sorting = {}
                        info.column_sorting[expr.name] = " ".join(sorting_parts)
            if backend == "clickhouse":
                info.clickhouse_type = idx.info.get("clickhouse_type", "minmax")
                info.clickhouse_granularity = idx.info.get("clickhouse_granularity", 1)
            indexes.append(info)
        if debug_timing:
            print(f"TIMING {model_class.__name__} indexes {len(indexes)} {time.time() - start:.3f}s", flush=True)
            start = time.time()

        clickhouse_options = {}
        object_type = "table"
        comment = getattr(dw_meta, "comment", None) if dw_meta else None
        checks = []
        uniques = []
        excludes = []
        pg_table = {}
        my_table = {}

        if dw_meta:
            checks = list(getattr(dw_meta, "pg_checks", []) or getattr(dw_meta, "checks", []))
            uniques = list(getattr(dw_meta, "pg_uniques", []) or getattr(dw_meta, "uniques", []))
            excludes = list(getattr(dw_meta, "pg_excludes", []))
            indexes_meta = getattr(dw_meta, "indexes", []) or []
            pg_indexes_meta = getattr(dw_meta, "pg_indexes", []) or []
            ch_indexes_meta = getattr(dw_meta, "ch_indexes", []) or []
            if not indexes:
                for idx_entry in list(indexes_meta) + list(pg_indexes_meta) + list(ch_indexes_meta):
                    if hasattr(idx_entry, "to_dict"):
                        idx_entry = idx_entry.to_dict()
                    if not isinstance(idx_entry, dict):
                        raise TypeError(
                            f"Index entries must be dicts or typed spec objects, "
                            f"got {type(idx_entry).__name__}"
                        )
                    idx_info = IndexInfo(
                        name=idx_entry.get("name"),
                        columns=list(idx_entry.get("columns", [])),
                        unique=bool(idx_entry.get("unique", False)),
                        using=idx_entry.get("using"),
                        where=idx_entry.get("where"),
                        include=idx_entry.get("include"),
                        nulls_not_distinct=bool(idx_entry.get("nulls_not_distinct", False)),
                        column_sorting=dict(idx_entry.get("column_sorting", {})) if idx_entry.get("column_sorting") else None,
                        clickhouse_type=idx_entry.get("clickhouse_type"),
                        clickhouse_granularity=idx_entry.get("clickhouse_granularity"),
                    )
                    indexes.append(idx_info)
            if isinstance(dw_meta.backend_table, dict):
                excluded_pg_keys = {"pg_indexes", "pg_checks", "pg_uniques"}
                pg_table = {k: v for k, v in dw_meta.backend_table.items() if k.startswith("pg_") and k not in excluded_pg_keys}
                my_table = {k: v for k, v in dw_meta.backend_table.items() if k.startswith("my_") and k != "my_indexes"}
            elif any(k.startswith("pg_") for k in getattr(dw_meta, "table_attrs", {})):
                excluded_pg_keys = {"pg_indexes", "pg_checks", "pg_uniques"}
                pg_table = {
                    k: v for k, v in dw_meta.table_attrs.items()
                    if k.startswith("pg_") and k not in excluded_pg_keys and v is not None
                }
            if not my_table and any(k.startswith("my_") for k in getattr(dw_meta, "table_attrs", {})):
                my_table = {
                    k: v for k, v in dw_meta.table_attrs.items()
                    if k.startswith("my_") and k != "my_indexes" and v is not None
                }

        if backend == "clickhouse":
            clickhouse_options = _ch_options_from_meta(model_class)
            object_type = _detect_ch_object_type(clickhouse_options)
        if debug_timing:
            print(f"TIMING {model_class.__name__} finalize {time.time() - start:.3f}s", flush=True)

        return ModelTable(
            name=table_name,
            columns=columns,
            clickhouse_options=clickhouse_options,
            object_type=object_type,
            foreign_keys=foreign_keys,
            indexes=indexes,
            comment=comment,
            checks=checks,
            uniques=uniques,
            excludes=excludes,
            pg_table=pg_table,
            my_table=my_table,
        )
    except DBWardenConfigError:
        raise
    except Exception:
        return None


def extract_column_info(
    column,
    db_name: str | None = None,
    backend: str | None = None,
) -> Optional[ModelColumn]:
    """
    Extract column information from a SQLAlchemy column.

    Args:
        column: SQLAlchemy column object.
        db_name: Database name for backend-specific type mapping.

    Returns:
        ModelColumn object or None if extraction fails.
    """
    try:
        name = column.name
        type_str = str(column.type)
        backend = backend or _get_backend_name(db_name)
        if backend == "postgresql":
            item_type = getattr(column.type, "item_type", None)
            if item_type is not None:
                type_str = "array"
            elif getattr(column.type, "enums", None) and getattr(column.type, "name", None):
                type_str = "enum"
            elif type_str.upper() == "JSONB":
                type_str = "jsonb"
            elif getattr(column.type, "timezone", False):
                type_str = "timestamptz"
        if backend == "clickhouse":
            clickhouse_type_override = column.info.get("clickhouse_type")
            if isinstance(clickhouse_type_override, str) and clickhouse_type_override.strip():
                type_str = clickhouse_type_override.strip()
        nullable = column.nullable
        primary_key = column.primary_key
        unique = column.unique
        autoincrement = column.autoincrement
        default = None
        if column.default:
            default_str = str(column.default)
            # SQLite doesn't support complex default expressions
            if default_str.startswith("ScalarElementColumnDefault"):
                # Extract the actual value from ScalarElementColumnDefault(True/False)
                import re

                match = re.search(r"ScalarElementColumnDefault\((.+)\)", default_str)
                if match:
                    value = match.group(1)
                    if value.lower() == "true":
                        default = "TRUE"
                    elif value.lower() == "false":
                        default = "FALSE"
                    elif value.isdigit():
                        default = value
                    else:
                        # Keep as-is for other simple values
                        default = value
            elif default_str.startswith("ColumnDefault"):
                # Handle ColumnDefault format
                import re

                match = re.search(r"ColumnDefault\((.+)\)", default_str)
                if match:
                    default = match.group(1)
            elif default_str.startswith("CallableColumnDefault"):
                # Handle CallableColumnDefault for Python callables like uuid4
                import re

                match = re.search(
                    r"CallableColumnDefault\(<function (\w+) at 0x[0-9a-f]+>\)",
                    default_str,
                )
                if match:
                    func_name = match.group(1)
                    # SQLite doesn't support Python callables as defaults
                    # For uuid4, we use a database-specific approach or omit
                    # Setting default to None so the column is created without a default
                    # The application must handle default value generation
                    default = None
                else:
                    # Try alternative pattern for callable defaults
                    match = re.search(r"CallableColumnDefault\((.+)\)", default_str)
                    if match:
                        default = None
            elif default_str.startswith("ColumnElementColumnDefault"):
                # Handle ColumnElementColumnDefault wrapping SQL expressions like func.now()
                # String repr looks like: ColumnElementColumnDefault(<sqlalchemy.sql.functions.now at 0x...; now>)
                import re

                match = re.search(r";\s*(\w+)\s*>", default_str)
                if match:
                    extracted = match.group(1)
                    # Wrap in parens if it looks like a function call
                    if extracted.upper() in ("CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME"):
                        default = extracted.upper()
                    else:
                        default = f"{extracted}()"
                else:
                    default = default_str
            else:
                default = default_str
        if column.server_default is not None and default is None:
            default = str(column.server_default.arg)

        type_str = _map_sqlalchemy_type_to_backend(
            type_str,
            is_primary_key=primary_key,
            db_name=db_name,
            autoincrement=autoincrement,
            backend=backend,
        )

        if _get_backend_name(db_name) == "sqlite":
            strict = is_strict_translation()
            translated_default, default_warning = translate_default_to_sqlite(
                default,
                strict=strict,
            )
            if default_warning:
                get_logger().warning(default_warning)
            default = translated_default

        foreign_key = None
        if column.foreign_keys:
            fk = list(column.foreign_keys)[0]
            colspec = fk._colspec
            # SQLite doesn't support table.column in REFERENCES, convert to format
            # SQLite expects: REFERENCES table(column) instead of table.column
            if "." in colspec:
                table, col = colspec.rsplit(".", 1)
                foreign_key = f"{table}({col})"
            else:
                foreign_key = colspec

        if foreign_key and backend == "clickhouse":
            raise DBWardenConfigError(
                f"Column '{column.table.name}.{column.name}' uses ForeignKey "
                f"constraint referencing '{foreign_key}', but ClickHouse does "
                f"not support foreign key constraints. Remove ForeignKey() and "
                f"use a plain mapped_column instead; the relationship is "
                f"logical only. If this model is shared across multiple "
                f"databases, move it to its own module and configure separate "
                f"model_paths per database."
            )

        codec = None
        comment = None
        pg_meta: dict[str, Any] = {}
        ch_meta: dict[str, Any] = {}
        my_meta: dict[str, Any] = {}
        if backend == "clickhouse":
            ch_codec = column.info.get("ch_codec")
            if isinstance(ch_codec, str) and ch_codec.strip():
                codec = ch_codec.strip()
            ch_key_map = {
                "ch_codec": "ch_codec",
                "ch_default_expression": "ch_default_expression",
                "ch_materialized": "ch_materialized",
                "ch_alias": "ch_alias",
                "ch_ttl": "ch_ttl",
                "ch_low_cardinality": "ch_low_cardinality",
                "ch_nullable": "ch_nullable",
                "ch_type": "ch_type",
            }
            for info_key, meta_key in ch_key_map.items():
                val = column.info.get(info_key)
                if val is not None:
                    ch_meta[meta_key] = val

            # Only set ch_type if not already set via ch_key_map above
            if "ch_type" not in ch_meta:
                clickhouse_type_override = column.info.get("clickhouse_type")
                if isinstance(clickhouse_type_override, str) and clickhouse_type_override.strip():
                    ch_type = clickhouse_type_override.strip()
                else:
                    ch_type = _map_sa_type_to_clickhouse(column)
                ch_meta["ch_type"] = ch_type

        if column.comment:
            comment = column.comment
        elif "dw_comment" in column.info:
            comment = column.info["dw_comment"]

        for key in (
            "pg_collation",
            "pg_storage",
            "pg_compression",
            "pg_generated",
            "pg_identity",
            "pg_identity_start",
            "pg_identity_increment",
            "pg_identity_min",
            "pg_identity_max",
        ):
            if key in column.info:
                pg_meta[key] = column.info[key]
        if backend == "postgresql":
            if item_type is not None:
                pg_meta["pg_type"] = {
                    "kind": "array",
                    "inner": item_type.__class__.__name__.lower().replace("varchar", "varchar").replace("text", "text"),
                    "dimensions": 1,
                }
            elif getattr(column.type, "enums", None) and getattr(column.type, "name", None):
                pg_meta["pg_enum_name"] = column.type.name
                pg_meta["pg_type"] = {
                    "kind": "enum",
                    "type_name": column.type.name,
                    "values": list(column.type.enums),
                }
            else:
                type_str_upper = type_str.upper()
                if type_str_upper == "TSVECTOR":
                    regconfig = getattr(column.type, "regconfig", None)
                    pg_type_entry: dict[str, Any] = {"kind": "tsvector"}
                    if regconfig:
                        pg_type_entry["config"] = str(regconfig)
                    pg_meta["pg_type"] = pg_type_entry

        for key in (
            "my_charset",
            "my_collate",
            "my_unsigned",
            "my_on_update",
        ):
            if key in column.info:
                my_meta[key] = column.info[key]

        return ModelColumn(
            name=name,
            type=type_str,
            nullable=nullable,
            primary_key=primary_key,
            unique=unique,
            default=default,
            foreign_key=foreign_key,
            codec=codec,
            comment=comment,
            pg_meta=pg_meta,
            ch_meta=ch_meta,
            my_meta=my_meta,
            autoincrement=autoincrement,
        )
    except Exception:
        return None


def compare_model_to_database(
    model_tables: List[ModelTable],
    db_tables: dict,
) -> List[SchemaDifference]:
    """
    Compare model definitions against database schema.

    Args:
        model_tables: List of tables from models.
        db_tables: Dictionary of tables from database inspection.

    Returns:
        List of SchemaDifference objects representing required changes.
    """
    differences = []

    model_table_names = {t.name for t in model_tables}
    db_table_names = set(db_tables.keys())

    new_tables = model_table_names - db_table_names
    dropped_tables = db_table_names - model_table_names

    for table_name in new_tables:
        for table in model_tables:
            if table.name == table_name:
                for col in table.columns:
                    differences.append(
                        SchemaDifference(
                            type="add_column",
                            table_name=table_name,
                            column_name=col.name,
                            sql=generate_add_column_sql(table_name, col),
                        )
                    )

    for table_name in dropped_tables:
        differences.append(
            SchemaDifference(
                type="drop_table",
                table_name=table_name,
                sql=f"DROP TABLE {table_name}",
            )
        )

    return differences


def generate_add_column_sql(
    table_name: str, column: ModelColumn, db_name: str | None = None
) -> str:
    """Generate SQL for adding a column."""
    _validate_identifier(table_name, "table_name")
    _validate_identifier(column.name, "column_name")
    
    backend = _get_backend_name(db_name)
    if backend == "clickhouse":
        col_type = column.ch_meta.get("ch_type", column.type)
    elif backend in ("mysql", "mariadb"):
        col_type = _render_mysql_column_type(column.type, column.my_meta)
    else:
        col_type = column.type
    is_serial = (
        column.type.upper() in ("SERIAL", "BIGSERIAL")
        if backend == "postgresql"
        else False
    )

    nullable_sql = "" if column.nullable or is_serial else "NOT NULL"
    default_sql = f" DEFAULT {column.default}" if column.default else ""
    fk_sql = f" REFERENCES {column.foreign_key}" if column.foreign_key else ""
    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
    if nullable_sql:
        sql += f" {nullable_sql}"
    if default_sql:
        sql += default_sql
    if backend in ("mysql", "mariadb"):
        sql = _append_mysql_column_attrs(sql, column.my_meta)
    if fk_sql:
        sql += fk_sql
    return sql


def generate_create_table_sql(table: ModelTable, db_name: str | None = None) -> str:
    """Generate CREATE TABLE SQL from a ModelTable."""
    backend = _get_backend_name(db_name)

    if backend == "clickhouse" and table.object_type == "dictionary":
        return generate_create_dictionary_sql(table)

    column_defs = []

    for col in table.columns:
        if backend == "clickhouse":
            col_type = col.ch_meta.get("ch_type", col.type)
        elif backend in ("mysql", "mariadb"):
            col_type = _render_mysql_column_type(col.type, col.my_meta)
        else:
            col_type = col.type
        col_def = f"    {col.name} {col_type}"
        is_serial = (
            col.type.upper() in ("SERIAL", "BIGSERIAL")
            if backend == "postgresql"
            else False
        )

        if not col.nullable and not is_serial:
            col_def += " NOT NULL"
        if backend != "clickhouse" and col.primary_key:
            col_def += " PRIMARY KEY"
        elif col.unique:
            col_def += " UNIQUE"
        if col.default and not is_serial:
            col_def += f" DEFAULT {col.default}"
        if backend in ("mysql", "mariadb"):
            col_def = _append_mysql_column_attrs(col_def, col.my_meta)
        if col.foreign_key:
            col_def += f" REFERENCES {col.foreign_key}"
        if backend == "clickhouse" and col.codec:
            col_def += f" CODEC({col.codec})"
        column_defs.append(col_def)

    if backend == "clickhouse":
        column_defs.extend(f"    {projection_sql}" for projection_sql in _render_clickhouse_projections(table))

    columns_sql = ",\n".join(column_defs)
    if backend == "clickhouse" and table.object_type == "materialized_view":
        sql = _generate_clickhouse_materialized_view_sql(table, columns_sql)
    else:
        sql = f"CREATE TABLE IF NOT EXISTS {table.name} (\n{columns_sql}\n)"
    if backend == "clickhouse":
        if table.object_type == "table":
            sql += _render_clickhouse_table_suffix(table)
    if backend in ("mysql", "mariadb") and table.my_table:
        parts: list[str] = []
        if table.my_table.get("my_engine"):
            parts.append(f"ENGINE={table.my_table['my_engine']}")
        if table.my_table.get("my_charset"):
            parts.append(f"DEFAULT CHARSET={table.my_table['my_charset']}")
        if table.my_table.get("my_collate"):
            parts.append(f"COLLATE={table.my_table['my_collate']}")
        if table.my_table.get("my_row_format"):
            parts.append(f"ROW_FORMAT={table.my_table['my_row_format']}")
        if table.my_table.get("my_auto_increment") is not None:
            parts.append(f"AUTO_INCREMENT={table.my_table['my_auto_increment']}")
        if parts:
            sql += " " + " ".join(parts)
    if backend == "postgresql" and table.pg_table:
        pg_partition = table.pg_table.get("pg_partition")
        if pg_partition:
            strategy = pg_partition.get("strategy", "RANGE")
            columns = pg_partition.get("columns", [])
            sql += f"\nPARTITION BY {strategy} ({', '.join(columns)})"
    return sql


def _generate_clickhouse_materialized_view_sql(
    table: ModelTable,
    columns_sql: str,
) -> str:
    options = table.clickhouse_options
    parts = [f"CREATE MATERIALIZED VIEW IF NOT EXISTS {table.name}"]
    to_table = options.get("ch_to_table")
    if to_table:
        parts[0] += f" TO {to_table}"
    parts[0] += f" (\n{columns_sql}\n)"

    if not to_table:
        engine_raw = options.get("ch_engine", "MergeTree")
        if isinstance(engine_raw, str):
            engine_name = engine_raw
            engine_args = []
        elif isinstance(engine_raw, tuple):
            engine_name = engine_raw[0] if engine_raw else "MergeTree"
            engine_args = list(str(a) for a in engine_raw[1:])
        else:
            engine_name = "MergeTree"
            engine_args = []
        if engine_args:
            parts.append(f"ENGINE = {engine_name}({', '.join(engine_args)})")
        else:
            parts.append(f"ENGINE = {engine_name}()")

    order_by = options.get("ch_order_by")
    if order_by is not None:
        parts.append(f"ORDER BY {_format_clickhouse_expression(order_by)}")

    primary_key = options.get("ch_primary_key")
    if primary_key:
        parts.append(f"PRIMARY KEY {_format_clickhouse_expression(primary_key)}")

    partition_by = options.get("ch_partition_by")
    if partition_by:
        parts.append(f"PARTITION BY {partition_by}")

    sample_by = options.get("ch_sample_by")
    if sample_by:
        parts.append(f"SAMPLE BY {sample_by}")

    ttl = options.get("ch_ttl")
    if ttl:
        parts.append("TTL " + ", ".join(ttl) if isinstance(ttl, list) else f"TTL {ttl}")

    select = options.get("ch_select_statement")
    if select:
        parts.append(f"AS {select}")
    return "\n".join(parts)


def generate_drop_table_sql(table_name: str) -> str:
    """Generate DROP TABLE SQL."""
    _validate_identifier(table_name, "table_name")
    return f"DROP TABLE {table_name}"


def generate_drop_object_sql(table: ModelTable) -> str:
    _validate_identifier(table.name, "table_name")
    if table.object_type == "materialized_view":
        return f"DROP VIEW {table.name}"
    if table.object_type == "dictionary":
        return f"DROP DICTIONARY {table.name}"
    return generate_drop_table_sql(table.name)


def generate_create_dictionary_sql(table: ModelTable) -> str:
    """Generate CREATE DICTIONARY SQL from a ModelTable."""
    options = table.clickhouse_options
    columns_sql = ",\n".join(
        f"    {col.name} {col.ch_meta.get('ch_type', col.type)}"
        for col in table.columns
    )
    pk = options.get("ch_dict_primary_key")
    if pk is None and table.columns:
        pk = table.columns[0].name
    primary_key_sql = f"PRIMARY KEY {_format_clickhouse_expression(pk)}"
    lifetime = options["ch_dict_lifetime"]
    lifetime_sql = f"LIFETIME({lifetime})" if isinstance(lifetime, str) else f"LIFETIME({lifetime})"
    return (
        f"CREATE DICTIONARY IF NOT EXISTS {table.name} (\n"
        f"{columns_sql}\n"
        f")\n"
        f"{primary_key_sql}\n"
        f"SOURCE({options['ch_dict_source']})\n"
        f"{lifetime_sql}\n"
        f"LAYOUT({options['ch_dict_layout']})"
    )


def extract_tables_from_database(sqlalchemy_url: str) -> dict[str, set[str]]:
    """
    Extract table names and their columns from the actual database.

    Args:
        sqlalchemy_url: SQLAlchemy database URL.

    Returns:
        Dictionary mapping table names to sets of column names.
    """
    from sqlalchemy import create_engine, inspect

    tables: dict[str, set[str]] = {}

    try:
        engine = create_engine(sqlalchemy_url)
        inspector = inspect(engine)

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_names = {col["name"].lower() for col in columns}
            tables[table_name] = column_names

        engine.dispose()
    except Exception:
        pass

    return tables


def _extract_create_table_columns(create_stmt: str) -> tuple[str | None, set[str]]:
    """Extract table name and column names from a CREATE TABLE statement.

    Uses balanced-paren matching to correctly extract the column list,
    handling CH-style ENGINE/SETTINGS clauses that follow the closing paren.
    """
    create_match = re.search(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(",
        create_stmt,
        re.IGNORECASE,
    )
    if not create_match:
        return None, set()

    table_name = create_match.group(1)
    start = create_match.end() - 1

    # Balanced-paren scan to find the column list closing ')'
    depth = 1
    i = start + 1
    while i < len(create_stmt) and depth > 0:
        if create_stmt[i] == '(':
            depth += 1
        elif create_stmt[i] == ')':
            depth -= 1
        i += 1

    if depth != 0:
        return table_name, set()

    columns_str = create_stmt[start + 1 : i - 1]
    column_names: set[str] = set()

    # Split on top-level commas (commas not inside nested parens)
    column_parts = re.split(r",\s*(?![^()]*\))", columns_str)
    for part in column_parts:
        part = part.strip()
        col_match = re.match(r"(\w+)", part, re.IGNORECASE)
        if col_match:
            col_name = col_match.group(1).lower()
            if col_name not in (
                "primary",
                "foreign",
                "unique",
                "check",
                "constraint",
            ):
                column_names.add(col_name)

    return table_name, column_names


def filter_model_tables_by_name(
    tables: list[ModelTable],
    allowed_names: list[str] | None,
) -> list[ModelTable]:
    """Filter a list of ModelTable objects to only those whose ``__tablename__``
    is in the configured ``allowed_names`` list.

    Returns the original list unchanged when ``allowed_names`` is ``None``.
    """
    if allowed_names is None:
        return tables
    allowed = set(allowed_names)
    return [t for t in tables if t.name in allowed]


def validate_model_tables_exist(
    discovered_tables: list[ModelTable],
    configured_names: list[str] | None,
    db_name: str,
) -> None:
    """Raise ``ConfigurationError`` if any name in ``configured_names`` does
    not appear in ``discovered_tables`` (pre-filter)."""
    if configured_names is None:
        return
    discovered = {t.name for t in discovered_tables}
    unknown = [n for n in configured_names if n not in discovered]
    if unknown:
        unknown_str = ", ".join(sorted(unknown))
        discovered_str = ", ".join(sorted(discovered)) if discovered else "(none)"
        raise DBWardenConfigError(
            f"Configured model_tables for database '{db_name}' contain unknown tables: "
            f"{unknown_str}. Discovered tables: {discovered_str}"
        )


def extract_tables_from_migrations(migrations_dir: str) -> dict[str, set[str]]:
    """
    Extract table names and their columns from existing migrations.

    Args:
        migrations_dir: Path to migrations directory.

    Returns:
        Dictionary mapping table names to sets of column names.
    """
    from dbwarden.engine.file_parser import parse_upgrade_statements

    tables: dict[str, set[str]] = {}

    if not os.path.exists(migrations_dir):
        return tables

    for filename in sorted(os.listdir(migrations_dir)):
        if not filename.endswith(".sql"):
            continue
        filepath = os.path.join(migrations_dir, filename)
        statements = parse_upgrade_statements(filepath)

        for stmt in statements:
            table_name, column_names = _extract_create_table_columns(stmt)
            if table_name and column_names:
                if table_name in tables:
                    tables[table_name].update(column_names)
                else:
                    tables[table_name] = column_names

    return tables
