from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dbwarden.config import get_database
from dbwarden.database.connection import get_db_connection
from dbwarden.output import console


_TYPE_MAP: dict[str, str] = {
    "INTEGER": "Integer",
    "BIGINT": "BigInteger",
    "SMALLINT": "SmallInteger",
    "VARCHAR": "String",
    "CHAR": "String",
    "TEXT": "Text",
    "BOOLEAN": "Boolean",
    "FLOAT": "Float",
    "REAL": "Float",
    "DOUBLE": "Float",
    "DECIMAL": "Numeric",
    "NUMERIC": "Numeric",
    "DATE": "Date",
    "DATETIME": "DateTime",
    "TIMESTAMP": "DateTime",
    "TIME": "Time",
    "BLOB": "LargeBinary",
    "BYTEA": "LargeBinary",
    "BINARY": "LargeBinary",
    "JSON": "JSON",
    "UUID": "String(36)",
    "ENUM": "Enum",
    "SERIAL": "Integer",
    "BIGSERIAL": "BigInteger",
    "TINYINT": "SmallInteger",
}


_CLICKHOUSE_MAP: dict[str, str] = {
    "Int8": "SmallInteger",
    "Int16": "SmallInteger",
    "Int32": "Integer",
    "Int64": "BigInteger",
    "UInt8": "SmallInteger",
    "UInt16": "Integer",
    "UInt32": "BigInteger",
    "UInt64": "BigInteger",
    "Float32": "Float",
    "Float64": "Float",
    "String": "String",
    "FixedString": "String",
    "Date": "Date",
    "DateTime": "DateTime",
    "DateTime64": "DateTime",
    "UUID": "String(36)",
    "JSON": "JSON",
}


def _parse_type(raw: str, dialect: str | None = None) -> str:
    raw_stripped = raw.strip()
    upper = raw_stripped.upper()

    is_nullable = upper.startswith("NULLABLE(")
    if is_nullable:
        inner = raw_stripped[9:-1].strip()
        inner_type = _parse_type(inner, dialect)
        return inner_type

    if upper.startswith("LOWCARDINALITY("):
        inner = raw_stripped[15:-1].strip()
        return _parse_type(inner, dialect)

    if upper.startswith("ARRAY("):
        inner = raw_stripped[6:-1].strip()
        inner_type = _parse_type(inner, dialect)
        return f"ARRAY({inner_type})"

    if upper.startswith("MAP("):
        return "JSON"

    if upper.startswith("ENUM"):
        return "Enum"

    if upper.startswith("DECIMAL") or upper.startswith("NUMERIC"):
        match = re.match(r"(DECIMAL|NUMERIC)\((\d+),\s*(\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"Numeric(precision={match.group(2)}, scale={match.group(3)})"
        return "Numeric"

    if upper.startswith("VARCHAR"):
        match = re.match(r"VARCHAR\((\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"String(length={match.group(1)})"
        return "String"

    if upper.startswith("CHAR"):
        match = re.match(r"CHAR\((\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"String(length={match.group(1)})"
        return "String"

    if upper.startswith("FLOAT"):
        return "Float"

    if upper.startswith("DOUBLE"):
        return "Float"

    if upper.startswith("DATETIME"):
        return "DateTime"

    if upper.startswith("TIMESTAMP"):
        return "DateTime"

    if upper.startswith("TINYINT"):
        if upper == "TINYINT(1)":
            return "Boolean"
        return "SmallInteger"

    if upper.startswith("BIGINT"):
        return "BigInteger"

    if upper.startswith("SMALLINT"):
        return "SmallInteger"

    if upper.startswith("SERIAL"):
        return "Integer"

    if upper.startswith("BIGSERIAL"):
        return "BigInteger"

    if dialect and dialect == "clickhouse":
        for ch_key, ch_val in _CLICKHOUSE_MAP.items():
            if raw_stripped.upper().startswith(ch_key.upper()):
                return ch_val

    for t_key, t_val in _TYPE_MAP.items():
        if upper.startswith(t_key):
            return t_val

    if upper.startswith("INT"):
        return "Integer"

    return "String"


def _format_default(default: Any) -> str | None:
    if default is None:
        return None
    raw = str(default).strip().strip("'\"")
    if not raw:
        return None
    upper = raw.upper()
    if upper == "NULL":
        return None
    if upper == "CURRENT_TIMESTAMP":
        return "func.now()"
    if upper == "CURRENT_DATE":
        return "func.current_date()"
    if upper == "CURRENT_TIME":
        return "func.current_time()"
    if upper in ("TRUE", "FALSE", "1", "0"):
        return raw
    if re.match(r"^\d+(\.\d+)?$", raw):
        return raw
    return repr(raw)


def _resolve_imports(columns: list[dict], has_relationships: bool) -> set[str]:
    imports: set[str] = {"Column"}
    for col in columns:
        sa_type = _parse_type(col["type"], col.get("dialect"))
        base_type = sa_type.split("(")[0].strip().upper()
        if base_type in ("STRING", "TEXT"):
            imports.add("String")
            imports.add("Text")
        elif base_type == "INTEGER":
            imports.add("Integer")
        elif base_type == "BIGINTEGER":
            imports.add("BigInteger")
        elif base_type == "SMALLINTEGER":
            imports.add("SmallInteger")
        elif base_type == "BOOLEAN":
            imports.add("Boolean")
        elif base_type == "FLOAT":
            imports.add("Float")
        elif base_type == "NUMERIC":
            imports.add("Numeric")
        elif base_type == "DATETIME":
            imports.add("DateTime")
        elif base_type == "DATE":
            imports.add("Date")
        elif base_type == "TIME":
            imports.add("Time")
        elif base_type == "LARGEBINARY":
            imports.add("LargeBinary")
        elif base_type == "JSON":
            imports.add("JSON")
        elif base_type == "ENUM":
            imports.add("Enum")
        if col.get("default") and "func.now()" in str(col["default"]):
            imports.add("func")
        if col.get("foreign_key"):
            imports.add("ForeignKey")
    if has_relationships:
        imports.add("relationship")
        imports.discard("ForeignKey")
        imports.add("ForeignKey")
    return imports


def _generate_table_code(
    table_name: str,
    columns: list[dict],
    clickhouse_options: dict | None = None,
    object_type: str = "table",
) -> str:
    class_name = "".join(part.capitalize() for part in re.split(r"[_\s]", table_name) if part)
    if not class_name:
        class_name = table_name.capitalize()

    lines: list[str] = []
    if object_type == "dictionary":
        ch_opts = dict(clickhouse_options or {})
        ch_opts["clickhouse_dictionary"] = True
        ch_args = _format_clickhouse_args(ch_opts)
        lines.append(f"class {class_name}(Base):")
        lines.append(f"    __tablename__ = {table_name!r}")
        if ch_args:
            lines.append(f"    __table_args__ = {ch_args}")
        for col in columns:
            col_line = _format_column(col)
            if col_line:
                lines.append(f"    {col_line}")
        return "\n".join(lines) + "\n"

    if object_type == "materialized_view":
        ch_opts = dict(clickhouse_options or {})
        ch_opts["clickhouse_mv"] = True
        ch_args = _format_clickhouse_args(ch_opts)
        lines.append(f"class {class_name}(Base):")
        lines.append(f"    __tablename__ = {table_name!r}")
        if ch_args:
            lines.append(f"    __table_args__ = {ch_args}")
        for col in columns:
            col_line = _format_column(col)
            if col_line:
                lines.append(f"    {col_line}")
        return "\n".join(lines) + "\n"

    lines.append(f"class {class_name}(Base):")
    lines.append(f"    __tablename__ = {table_name!r}")
    if clickhouse_options:
        ch_args = _format_clickhouse_args(clickhouse_options)
        if ch_args:
            lines.append(f"    __table_args__ = {ch_args}")
    for col in columns:
        col_line = _format_column(col)
        if col_line:
            lines.append(f"    {col_line}")
    return "\n".join(lines) + "\n"


def _format_column(col: dict) -> str:
    col_name = col["name"]
    sa_type = _parse_type(col["type"], col.get("dialect"))

    col_args = [f"Column({col_name!r}, {sa_type}"]
    if col.get("primary_key"):
        col_args.append("primary_key=True")
    if not col.get("nullable", True):
        col_args.append("nullable=False")
    if col.get("unique"):
        col_args.append("unique=True")
    if col.get("foreign_key"):
        col_args.append(f"ForeignKey('{col['foreign_key']}')")
    default = _format_default(col.get("default"))
    if default is not None:
        col_args.append(f"default={default}")
    if col.get("autoincrement") is False:
        col_args.append("autoincrement=False")
    col_args.append(")")
    return ",\n        ".join(col_args)


def _format_clickhouse_args(options: dict) -> str:
    parts: list[str] = []
    for key in (
        "clickhouse_engine",
        "clickhouse_order_by",
        "clickhouse_primary_key",
        "clickhouse_partition_by",
        "clickhouse_sample_by",
        "clickhouse_ttl",
        "clickhouse_mv",
        "clickhouse_mv_query",
        "clickhouse_mv_engine",
        "clickhouse_mv_order_by",
        "clickhouse_mv_populate",
        "clickhouse_projections",
        "clickhouse_zookeeper_path",
        "clickhouse_replica_name",
        "clickhouse_dictionary",
        "clickhouse_dict_layout",
        "clickhouse_dict_source",
        "clickhouse_dict_lifetime",
        "clickhouse_dict_primary_key",
    ):
        if key in options and options[key] is not None:
            value = options[key]
            if isinstance(value, str):
                parts.append(f"    {key!r}: {value!r},")
            elif isinstance(value, bool):
                parts.append(f"    {key!r}: {str(value)},")
            elif isinstance(value, list):
                items = ", ".join(repr(v) for v in value)
                parts.append(f"    {key!r}: [{items}],")
            elif isinstance(value, tuple):
                items = ", ".join(repr(v) for v in value)
                parts.append(f"    {key!r}: ({items}),")
            elif isinstance(value, int):
                parts.append(f"    {key!r}: {value!r},")
            else:
                parts.append(f"    {key!r}: {value!r},")
    if not parts:
        return ""
    return "{\n" + "\n".join(parts) + "\n}"


def _write_models(output_dir: str, tables: list[dict], single_file: bool) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    has_relationships = any(
        col.get("foreign_key") for table in tables for col in table["columns"]
    )

    if single_file:
        all_imports: set[str] = set()
        all_classes: list[str] = []
        for table in tables:
            for col in table["columns"]:
                col["dialect"] = table.get("dialect")
            all_imports |= _resolve_imports(table["columns"], has_relationships)
            all_classes.append(
                _generate_table_code(
                    table["name"],
                    table["columns"],
                    table.get("clickhouse_options"),
                    table.get("object_type", "table"),
                )
            )

        imports = _render_imports(all_imports)
        content = (
            "from sqlalchemy import " + ", ".join(sorted(imports)) + "\n"
            if imports
            else ""
        )
        if has_relationships:
            content += "from sqlalchemy.orm import relationship\n"
        content += (
            "from sqlalchemy.ext.declarative import declarative_base\n\n\n"
            "Base = declarative_base()\n\n\n"
        )
        content += "\n\n".join(all_classes)
        (out_path / "models.py").write_text(content, encoding="utf-8")
        return

    seen_relations = False
    for table in tables:
        for col in table["columns"]:
            col["dialect"] = table.get("dialect")
        imports = _resolve_imports(table["columns"], has_relationships)
        has_rel = has_relationships and any(
            col.get("foreign_key") for col in table["columns"]
        )
        content_lines: list[str] = []
        content_lines.append("from sqlalchemy import " + ", ".join(sorted(imports)) + "\n")
        if has_rel and not seen_relations:
            content_lines.append("from sqlalchemy.orm import relationship\n")
            seen_relations = True
        content_lines.append("from sqlalchemy.ext.declarative import declarative_base\n\n\n")
        content_lines.append("Base = declarative_base()\n\n\n")
        content_lines.append(
            _generate_table_code(
                table["name"],
                table["columns"],
                table.get("clickhouse_options"),
                table.get("object_type", "table"),
            )
        )
        safe_name = table["name"].lower().replace("-", "_")
        (out_path / f"{safe_name}.py").write_text("".join(content_lines), encoding="utf-8")


def _render_imports(imports: set[str]) -> set[str]:
    result: set[str] = set()
    for imp in sorted(imports):
        if imp in ("Column", "ForeignKey", "func"):
            continue
        result.add(imp)
    result.add("Column")
    return result


def generate_models_cmd(
    output: str = "models",
    tables: str | None = None,
    exclude_tables: str | None = None,
    clickhouse_engines: bool = False,
    relationships: bool = False,
    dialect: str | None = None,
    single_file: bool = False,
    database: str | None = None,
) -> None:
    config = get_database(database)
    actual_dialect = dialect or config.database_type

    if tables:
        table_filter = {t.strip() for t in tables.split(",")}
    else:
        table_filter = None

    if exclude_tables:
        exclude_set = {t.strip() for t in exclude_tables.split(",")}
    else:
        exclude_set = set()

    with get_db_connection(database) as connection:
        from sqlalchemy import inspect

        inspector = inspect(connection)
        all_table_names = inspector.get_table_names()

        target_tables = all_table_names
        if table_filter:
            target_tables = [t for t in target_tables if t in table_filter]
        target_tables = [t for t in target_tables if t not in exclude_set]

        if not target_tables:
            console.print("No tables found matching the given criteria.", style="yellow")
            return

        tables_data: list[dict] = []

        for table_name in target_tables:
            columns_info: list[dict] = []

            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_columns = set(pk_constraint.get("constrained_columns", []))

            unique_constraints = inspector.get_unique_constraints(table_name)
            unique_columns: set[str] = set()
            for uc in unique_constraints:
                unique_columns.update(uc.get("column_names", []))

            raw_columns = inspector.get_columns(table_name)
            foreign_keys_raw = inspector.get_foreign_keys(table_name)

            fk_map: dict[str, str] = {}
            for fk in foreign_keys_raw:
                for constrained, referred in zip(
                    fk.get("constrained_columns", []),
                    fk.get("referred_columns", []) or [None] * len(fk.get("constrained_columns", [])),
                ):
                    if referred:
                        fk_map[constrained] = f"{fk['referred_table']}({referred})"

            for col in raw_columns:
                col_name = col["name"]
                col_type_str = str(col["type"])
                col_nullable = col.get("nullable", True)
                col_default = col.get("default")
                col_primary = col_name in pk_columns
                col_unique = col_name in unique_columns
                col_fk = fk_map.get(col_name)

                autoinc = getattr(col["type"], "autoincrement", None)
                if autoinc is None:
                    autoinc = col_primary and col_type_str.upper() in ("INTEGER", "INT", "BIGINT")

                columns_info.append({
                    "name": col_name,
                    "type": col_type_str,
                    "nullable": col_nullable,
                    "default": col_default,
                    "primary_key": col_primary,
                    "unique": col_unique,
                    "foreign_key": col_fk,
                    "autoincrement": autoinc,
                    "dialect": actual_dialect,
                })

            ch_options: dict = {}
            if actual_dialect == "clickhouse" and clickhouse_engines:
                ch_options = _extract_clickhouse_options(connection, table_name)

            tables_data.append({
                "name": table_name,
                "columns": columns_info,
                "clickhouse_options": ch_options if ch_options else None,
                "object_type": "table",
                "dialect": actual_dialect,
            })

    output_dir = Path(output)
    _write_models(str(output_dir), tables_data, single_file=single_file)
    console.print(
        f"Generated {len(tables_data)} model(s) in '{output_dir}/'",
        style="green",
    )

    if actual_dialect == "clickhouse":
        for t in tables_data:
            if t.get("clickhouse_options"):
                for key in ("clickhouse_engine", "clickhouse_mv_query"):
                    if key in t["clickhouse_options"]:
                        break
                else:
                    console.print(
                        f"  WARNING: ClickHouse engine metadata for '{t['name']}' may be incomplete.",
                        style="yellow",
                    )


def _extract_clickhouse_options(connection, table_name: str) -> dict:
    from sqlalchemy import text

    result = connection.execute(
        text(
            "SELECT engine, sorting_key, primary_key, partition_key, sampling_key, create_table_query "
            "FROM system.tables WHERE database = currentDatabase() AND name = :name"
        ),
        parameters={"name": table_name},
    )
    row = result.fetchone()
    if not row:
        return {}

    from dbwarden.engine.safety import (
        _parse_tuple_expression,
        _clean_expression,
        _parse_ttl_expressions,
        _parse_projection_names,
        _parse_mv_query,
        _parse_zookeeper_path,
        _parse_replica_name,
    )

    options: dict = {}
    engine = getattr(row, "engine", "") or ""
    if engine:
        options["clickhouse_engine"] = engine
    sorting_key = _parse_tuple_expression(getattr(row, "sorting_key", None))
    if sorting_key:
        options["clickhouse_order_by"] = sorting_key
    primary_key = _parse_tuple_expression(getattr(row, "primary_key", None))
    if primary_key:
        options["clickhouse_primary_key"] = primary_key
    partition_key = _clean_expression(getattr(row, "partition_key", None))
    if partition_key:
        options["clickhouse_partition_by"] = partition_key
    sampling_key = _clean_expression(getattr(row, "sampling_key", None))
    if sampling_key:
        options["clickhouse_sample_by"] = sampling_key

    create_query = getattr(row, "create_table_query", "") or ""
    ttl = _parse_ttl_expressions(create_query)
    if ttl:
        options["clickhouse_ttl"] = ttl
    projections = _parse_projection_names(create_query)
    if projections:
        options["clickhouse_projections"] = [{"name": p, "query": ""} for p in projections]
    mv_query = _parse_mv_query(create_query)
    if mv_query:
        options["clickhouse_mv_query"] = mv_query
    zk_path = _parse_zookeeper_path(create_query, engine)
    if zk_path:
        options["clickhouse_zookeeper_path"] = zk_path
    replica = _parse_replica_name(create_query, engine)
    if replica:
        options["clickhouse_replica_name"] = replica

    if engine.upper() == "DICTIONARY":
        options["clickhouse_dictionary"] = True

    if create_query.strip().upper().startswith("CREATE MATERIALIZED VIEW"):
        options["clickhouse_mv"] = True

    return options
