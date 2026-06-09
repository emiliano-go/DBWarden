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


def _strip_codec_wrapper(codec_expr: str) -> str:
    m = re.match(r"^CODEC\((.+)\)$", codec_expr.strip(), re.IGNORECASE)
    return m.group(1) if m else codec_expr.strip()


def _parse_type(raw: str, dialect: str | None = None) -> str:
    raw_stripped = raw.strip()
    upper = raw_stripped.upper()

    if dialect == "postgresql":
        if upper == "JSONB":
            return "JSONB"
        if upper == "UUID":
            return "UUID(as_uuid=True)"
        if upper.endswith("[]"):
            inner = _parse_type(raw_stripped[:-2], dialect)
            return f"ARRAY({inner})"

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


def _format_pg_type(col: dict) -> str | None:
    if col.get("pg_enum_values") and col.get("pg_enum_name"):
        values = ", ".join(repr(v) for v in col["pg_enum_values"])
        return f"Enum({values}, name={col['pg_enum_name']!r})"
    if col.get("pg_array_inner"):
        inner = _parse_type(col["pg_array_inner"], "postgresql")
        return f"ARRAY({inner})"
    if col.get("pg_timestamptz"):
        return "DateTime(timezone=True)"
    pg_type = col.get("pg_type") or {}
    kind = pg_type.get("kind")
    if kind == "tsvector":
        config = pg_type.get("config")
        if config:
            return f"TSVECTOR({config!r})"
        return "TSVECTOR"
    if kind == "range":
        raw_type = col.get("type", "").upper().strip()
        type_map = {
            "TSTZRANGE": "TSTZRANGE",
            "TSRANGE": "TSRANGE",
            "DATERANGE": "DATERANGE",
            "INT4RANGE": "INT4RANGE",
            "INT8RANGE": "INT8RANGE",
            "NUMRANGE": "NUMRANGE",
        }
        return type_map.get(raw_type, "TSTZRANGE")
    return None


def _format_default(default: Any) -> str | None:
    if default is None:
        return None
    raw = str(default).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        raw = raw[1:-1]
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
    if upper in ("TRUE", "FALSE"):
        return raw.capitalize()
    if upper in ("1", "0"):
        return raw
    if re.match(r"^\d+(\.\d+)?$", raw):
        return raw
    return repr(raw)


def _resolve_imports(columns: list[dict], has_relationships: bool) -> set[str]:
    imports: set[str] = {"Column"}
    for col in columns:
        sa_type = _format_pg_type(col) or _parse_type(col["type"], col.get("dialect"))
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
        elif base_type == "ARRAY":
            imports.add("ARRAY")
            inner = sa_type[6:-1]
            if inner.startswith("Text"):
                imports.add("Text")
            elif inner.startswith("String"):
                imports.add("String")
            elif inner.startswith("Integer"):
                imports.add("Integer")
        if col.get("default") and "func.now()" in str(col["default"]):
            imports.add("func")
        if col.get("server_default"):
            imports.add("text")
        if col.get("foreign_key"):
            imports.add("ForeignKey")
    return imports


def _resolve_postgresql_imports(columns: list[dict]) -> set[str]:
    imports: set[str] = set()
    for col in columns:
        raw_type = str(col.get("type", ""))
        upper = raw_type.upper()
        if upper == "JSONB":
            imports.add("JSONB")
        elif upper == "UUID":
            imports.add("UUID")
        elif upper.endswith("[]") or col.get("pg_array_inner"):
            imports.add("ARRAY")
        elif upper == "TSVECTOR":
            imports.add("TSVECTOR")
        elif upper.endswith("RANGE"):
            imports.add(upper)
    return imports


def _format_meta_value(value: Any, indent: str = "        ") -> list[str]:
    if isinstance(value, str):
        return [f"{indent}{value!r}"]
    if isinstance(value, list):
        if not value:
            return [f"{indent}[]"]
        lines = [f"{indent}["]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{indent}    {item!r},")
            else:
                lines.append(f"{indent}    {item!r},")
        lines.append(f"{indent}]")
        return lines
    return [f"{indent}{value!r}"]


def _render_postgresql_meta(columns: list[dict], pg_meta: dict | None = None) -> list[str]:
    if not pg_meta and not any(col.get("pg_meta") or col.get("comment") for col in columns):
        return []

    lines = ["    class Meta(PGTableMeta):"]
    pg_meta = pg_meta or {}
    for key, value in pg_meta.items():
        if key == "comment":
            lines.append(f"        comment = {value!r}")
        else:
            rendered = _format_meta_value(value)
            if len(rendered) == 1:
                lines.append(f"        {key} = {rendered[0].strip()}")
            else:
                lines.append(f"        {key} = {rendered[0].strip()}")
                lines.extend(rendered[1:])

    for col in columns:
        field_meta: dict[str, Any] = {}
        if col.get("comment"):
            field_meta["comment"] = col["comment"]
        field_meta.update(col.get("pg_meta") or {})
        if not field_meta:
            continue
        lines.append("")
        lines.append(f"        class {col['name']}(PGColumnMeta):")
        for key, value in field_meta.items():
            lines.append(f"            {key} = {value!r}")

    return lines


def _generate_table_code(
    table_name: str,
    columns: list[dict],
    clickhouse_options: dict | None = None,
    object_type: str = "table",
    pg_meta: dict | None = None,
) -> str:
    class_name = "".join(part.capitalize() for part in re.split(r"[_\s]", table_name) if part)
    if not class_name:
        class_name = table_name.capitalize()

    lines: list[str] = []
    lines.append(f"class {class_name}(Base):")
    lines.append(f"    __tablename__ = {table_name!r}")
    for col in columns:
        col_line = _format_column(col)
        if col_line:
            lines.append(f"    {col_line}")
    if clickhouse_options:
        lines.append("")
        lines.append("    class Meta(CHTableMeta):")
        lines.extend(_render_ch_meta(columns, clickhouse_options, object_type))
    if pg_meta or any(col.get("pg_meta") or col.get("comment") for col in columns):
        lines.append("")
        lines.extend(_render_postgresql_meta(columns, pg_meta))
    return "\n".join(lines) + "\n"


def _render_ch_meta(columns: list[dict], options: dict, object_type: str) -> list[str]:
    lines: list[str] = []

    engine_raw = options.get("ch_engine_raw")
    if engine_raw is not None:
        if hasattr(engine_raw, "name"):
            eng_name = repr(getattr(engine_raw, "name"))
            eng_args = getattr(engine_raw, "args", None)
            zk = getattr(engine_raw, "zookeeper_path", None)
            replica = getattr(engine_raw, "replica_name", None)
            settings = getattr(engine_raw, "settings", None)
            parts = [f"        ch_engine = ChEngineSpec({eng_name}"]
            if eng_args:
                parts.append(f"args=({', '.join(repr(a) for a in eng_args)},)")
            if zk is not None:
                parts.append(f"zookeeper_path={zk!r}")
            if replica is not None:
                parts.append(f"replica_name={replica!r}")
            if settings is not None:
                parts.append(f"settings={settings!r}")
            lines.append(", ".join(parts) + ")")
        elif isinstance(engine_raw, dict) and engine_raw.get("name"):
            eng_name = repr(engine_raw["name"])
            eng_args = engine_raw.get("args")
            zk = engine_raw.get("zookeeper_path")
            replica = engine_raw.get("replica_name")
            settings = engine_raw.get("settings")
            parts = [f"        ch_engine = ChEngineSpec({eng_name}"]
            if eng_args:
                parts.append(f"args=({', '.join(repr(a) for a in eng_args)},)")
            if zk is not None:
                parts.append(f"zookeeper_path={zk!r}")
            if replica is not None:
                parts.append(f"replica_name={replica!r}")
            if settings is not None:
                parts.append(f"settings={settings!r}")
            lines.append(", ".join(parts) + ")")
        else:
            lines.append(f"        ch_engine = {engine_raw!r}")
    elif options.get("ch_engine"):
        lines.append(f"        ch_engine = {options['ch_engine']!r}")

    for key in (
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
    ):
        value = options.get(key)
        if value is None:
            continue
        if key == "ch_dictionary" and value is True:
            lines.append("        ch_dictionary = True")
        else:
            lines.append(f"        {key} = {value!r}")

    projections = options.get("ch_projections") or []
    if projections:
        lines.append("        ch_projections = [")
        for projection in projections:
            if isinstance(projection, dict):
                lines.append(
                    f"            ProjectionSpec({projection.get('name')!r}, {projection.get('query', '')!r}),"
                )
            else:
                lines.append(f"            ProjectionSpec({getattr(projection, 'name', '')!r}, {getattr(projection, 'query', '')!r}),")
        lines.append("        ]")

    for col in columns:
        ch_meta = col.get("ch_meta") or {}
        if not ch_meta and not col.get("comment"):
            continue
        lines.append("")
        lines.append(f"        class {col['name']}(CHColumnMeta):")
        has_content = False
        if col.get("comment"):
            lines.append(f"            comment = {col['comment']!r}")
            has_content = True
        for key in ("ch_codec", "ch_default_expression", "ch_materialized", "ch_alias", "ch_ttl"):
            if ch_meta.get(key) is not None:
                lines.append(f"            {key} = {ch_meta[key]!r}")
                has_content = True
        if ch_meta.get("ch_low_cardinality"):
            lines.append("            ch_low_cardinality = True")
            has_content = True
        if ch_meta.get("ch_nullable"):
            lines.append("            ch_nullable = True")
            has_content = True
        if not has_content:
            lines.append("            pass")

    return lines


def _format_column(col: dict) -> str:
    col_name = col["name"]
    sa_type = _format_pg_type(col) or _parse_type(col["type"], col.get("dialect"))

    col_args = [f"{col_name} = Column({col_name!r}, {sa_type}"]
    if col.get("primary_key"):
        col_args.append("primary_key=True")
    if not col.get("nullable", True):
        col_args.append("nullable=False")
    if col.get("unique"):
        col_args.append("unique=True")
    if col.get("foreign_key"):
        fk_opts = col.get("fk_options", {})
        fk_parts: list[str] = []
        for opt_key, sa_key in (("ondelete", "ondelete"), ("onupdate", "onupdate"), ("deferrable", "deferrable")):
            val = fk_opts.get(opt_key)
            if opt_key == "deferrable":
                if val:
                    fk_parts.append("deferrable=True")
            elif val and val != "NO ACTION":
                fk_parts.append(f"{sa_key}={val!r}")
        if fk_parts:
            col_args.append(f"ForeignKey('{col['foreign_key']}', {', '.join(fk_parts)})")
        else:
            col_args.append(f"ForeignKey('{col['foreign_key']}')")
    default = _format_default(col.get("default"))
    if default is not None:
        col_args.append(f"default={default}")
    if col.get("server_default"):
        col_args.append(f"server_default=text({col['server_default']!r})")
    if col.get("autoincrement") is False:
        col_args.append("autoincrement=False")
    col_args.append(")")
    return ",\n        ".join(col_args)


def _write_models(output_dir: str, tables: list[dict], single_file: bool) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    has_relationships = False

    if single_file:
        all_imports: set[str] = set()
        pg_dialect_imports: set[str] = set()
        ch_meta_imports: set[str] = set()
        all_classes: list[str] = []
        for table in tables:
            for col in table["columns"]:
                col["dialect"] = table.get("dialect")
            all_imports |= _resolve_imports(table["columns"], has_relationships)
            if table.get("dialect") == "postgresql":
                pg_dialect_imports |= _resolve_postgresql_imports(table["columns"])
            if table.get("clickhouse_options"):
                ch_meta_imports.update({"CHColumnMeta", "CHTableMeta", "ChEngineSpec", "ProjectionSpec"})
            all_classes.append(
                _generate_table_code(
                    table["name"],
                    table["columns"],
                    table.get("clickhouse_options"),
                    table.get("object_type", "table"),
                    table.get("pg_meta"),
                )
            )

        imports = _render_imports(all_imports)
        pg_meta_imports: set[str] = set()
        for table in tables:
            if any(col.get("pg_meta") for col in table["columns"]):
                pg_meta_imports.add("PGColumnMeta")
        if any(table.get("pg_meta") for table in tables):
            pg_meta_imports.add("PGTableMeta")

        content = (
            "from sqlalchemy import " + ", ".join(sorted(imports)) + "\n"
            if imports
            else ""
        )
        if pg_dialect_imports:
            content += "from sqlalchemy.dialects.postgresql import " + ", ".join(sorted(pg_dialect_imports)) + "\n"
        content += (
            "from sqlalchemy.ext.declarative import declarative_base\n\n\n"
            "Base = declarative_base()\n\n\n"
        )
        if pg_meta_imports:
            content += "from dbwarden import " + ", ".join(sorted(pg_meta_imports)) + "\n\n\n"
        if ch_meta_imports:
            content += "from dbwarden import " + ", ".join(sorted(ch_meta_imports)) + "\n\n\n"
        content += "\n\n".join(all_classes)
        (out_path / "models.py").write_text(content, encoding="utf-8")
        return

    for table in tables:
        for col in table["columns"]:
            col["dialect"] = table.get("dialect")
        imports = _resolve_imports(table["columns"], has_relationships)
        pg_dialect_imports = _resolve_postgresql_imports(table["columns"]) if table.get("dialect") == "postgresql" else set()
        content_lines: list[str] = []
        content_lines.append("from sqlalchemy import " + ", ".join(sorted(imports)) + "\n")
        if pg_dialect_imports:
            content_lines.append("from sqlalchemy.dialects.postgresql import " + ", ".join(sorted(pg_dialect_imports)) + "\n")
        content_lines.append("from sqlalchemy.ext.declarative import declarative_base\n\n\n")
        content_lines.append("Base = declarative_base()\n\n\n")
        needs_pg_base: set[str] = set()
        if any(col.get("pg_meta") for col in table["columns"]):
            needs_pg_base.add("PGColumnMeta")
        if table.get("pg_meta"):
            needs_pg_base.add("PGTableMeta")
        if needs_pg_base:
            content_lines.append("from dbwarden import " + ", ".join(sorted(needs_pg_base)) + "\n\n\n")
        if table.get("clickhouse_options"):
            content_lines.append("from dbwarden import CHColumnMeta, CHTableMeta, ChEngineSpec, ProjectionSpec\n\n\n")
        content_lines.append(
            _generate_table_code(
                table["name"],
                table["columns"],
                table.get("clickhouse_options"),
                table.get("object_type", "table"),
                table.get("pg_meta"),
            )
        )
        safe_name = table["name"].lower().replace("-", "_")
        (out_path / f"{safe_name}.py").write_text("".join(content_lines), encoding="utf-8")


def _render_imports(imports: set[str]) -> set[str]:
    result: set[str] = set()
    for imp in sorted(imports):
        if imp in ("Column", "func"):
            continue
        result.add(imp)
    result.add("Column")
    return result


def _extract_postgresql_meta(inspector, connection, table_name: str, raw_columns: list[dict], indexes: list[dict], checks: list[dict], uniques: list[dict]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    from sqlalchemy import text
    table_meta: dict[str, Any] = {}
    column_meta: dict[str, dict[str, Any]] = {}

    try:
        comment = inspector.get_table_comment(table_name)
        if comment and comment.get("text"):
            table_meta["comment"] = comment["text"]
    except Exception:
        pass

    pg_indexes: list[dict[str, Any]] = []
    for idx in indexes:
        dialect_options = idx.get("dialect_options", {})
        entry: dict[str, Any] = {
            "name": idx.get("name"),
            "columns": list(idx.get("column_names", [])),
            "unique": bool(idx.get("unique", False)),
        }
        if dialect_options.get("postgresql_using"):
            entry["using"] = dialect_options["postgresql_using"]
        if dialect_options.get("postgresql_where"):
            entry["where"] = dialect_options["postgresql_where"]
        if idx.get("include_columns"):
            entry["include"] = list(idx.get("include_columns", []))
        if dialect_options.get("postgresql_nulls_not_distinct"):
            entry["nulls_not_distinct"] = True
        idx_name = idx.get("name")
        if idx_name:
            try:
                sort_rows = connection.execute(
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
                    entry["column_sorting"] = sorting
            except Exception:
                try:
                    connection.rollback()
                except Exception:
                    pass
        pg_indexes.append(entry)
    if pg_indexes:
        table_meta["pg_indexes"] = pg_indexes

    if checks:
        no_inherit_checks: dict[str, bool] = {}
        try:
            rows = connection.execute(
                text("SELECT conname, connoinherit FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'c'"),
                {"t": table_name},
            ).fetchall()
            for r in rows:
                if r[1]:
                    no_inherit_checks[r[0]] = True
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
        table_meta["pg_checks"] = []
        for ck in checks:
            entry: dict[str, Any] = {"name": ck.get("name"), "expression": ck.get("sqltext", "")}
            if ck.get("name") in no_inherit_checks:
                entry["no_inherit"] = True
            table_meta["pg_checks"].append(entry)
    if uniques:
        table_meta["pg_uniques"] = [
            {"name": uq.get("name"), "columns": list(uq.get("column_names", []))}
            for uq in uniques
        ]

    try:
        rows = connection.execute(
            text("SELECT unnest(COALESCE(reloptions, '{}')) FROM pg_class WHERE relname = :t"),
            {"t": table_name},
        ).fetchall()
        for row in rows:
            kv = row[0].split("=", 1)
            if len(kv) == 2:
                key = f"pg_{kv[0]}"
                val = kv[1]
                if val.isdigit():
                    val = int(val)
                table_meta[key] = val
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        row = connection.execute(
            text("SELECT relpersistence FROM pg_class WHERE relname = :t"),
            {"t": table_name},
        ).fetchone()
        if row and row[0] == 'u':
            table_meta["pg_unlogged"] = True
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        row = connection.execute(
            text("SELECT spcname FROM pg_tablespace t JOIN pg_class c ON c.reltablespace = t.oid WHERE c.relname = :t"),
            {"t": table_name},
        ).fetchone()
        if row:
            table_meta["pg_tablespace"] = row[0]
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        rows = connection.execute(
            text("SELECT inhparent::regclass::text FROM pg_inherits WHERE inhrelid = CAST(:t AS regclass)"),
            {"t": table_name},
        ).fetchall()
        parents = [r[0] for r in rows]
        if parents:
            table_meta["pg_inherits"] = parents[0]
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        part_row = connection.execute(
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
            table_meta["pg_partition"] = {
                "strategy": strategy,
                "columns": part_columns,
            }
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        rows = connection.execute(
            text("SELECT conname, pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'x'"),
            {"t": table_name},
        ).fetchall()
        excludes = [{"name": r[0], "expression": r[1]} for r in rows]
        if excludes:
            table_meta["pg_excludes"] = excludes
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    for col in raw_columns:
        meta: dict[str, Any] = {}
        if col.get("comment"):
            meta["comment"] = col["comment"]
        collation = col.get("collation") or getattr(col.get("type"), "collation", None)
        if collation:
            meta["pg_collation"] = collation
        if isinstance(col.get("identity"), dict):
            identity = col["identity"]
            always = identity.get("always")
            if always is True:
                meta["pg_identity"] = "always"
            elif always is False:
                meta["pg_identity"] = "by_default"
            for src, dst in (("start", "pg_identity_start"), ("increment", "pg_identity_increment"), ("minvalue", "pg_identity_min"), ("maxvalue", "pg_identity_max")):
                if identity.get(src) is not None:
                    meta[dst] = identity[src]
        if isinstance(col.get("computed"), dict) and col["computed"].get("sqltext"):
            meta["pg_generated"] = col["computed"]["sqltext"]
        if meta:
            column_meta[col["name"]] = meta

    # Capture storage and compression from pg_attribute for all columns
    try:
        rows = connection.execute(
            text("SELECT a.attname, a.attstorage, a.attcompression FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid WHERE c.relname = :t AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"),
            {"t": table_name},
        ).fetchall()
        storage_map = {'p': 'PLAIN', 'm': 'MAIN', 'e': 'EXTERNAL', 'x': 'EXTENDED'}
        for r in rows:
            cname = r[0]
            if cname in column_meta or True:
                meta = column_meta.get(cname, {}) or {}
                if r[1]:
                    meta["pg_storage"] = storage_map.get(r[1], r[1])
                if r[2]:
                    meta["pg_compression"] = r[2]
                if meta:
                    column_meta[cname] = meta
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    return table_meta, column_meta


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

        target_tables = [t for t in all_table_names if not t.startswith(".")]
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
            indexes_info = inspector.get_indexes(table_name)
            checks_info = inspector.get_check_constraints(table_name)
            unique_columns: set[str] = set()
            for uc in unique_constraints:
                cols = uc.get("column_names", [])
                if len(cols) == 1:
                    unique_columns.update(cols)

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

                entry = {
                    "name": col_name,
                    "type": col_type_str,
                    "nullable": col_nullable,
                    "default": col_default,
                    "server_default": col_default,
                    "primary_key": col_primary,
                    "unique": col_unique,
                    "foreign_key": col_fk,
                    "autoincrement": autoinc,
                    "dialect": actual_dialect,
                }

                if actual_dialect == "postgresql":
                    type_obj = col["type"]
                    if getattr(type_obj, "item_type", None) is not None:
                        entry["pg_array_inner"] = str(type_obj.item_type)
                    if getattr(type_obj, "enums", None) and getattr(type_obj, "name", None):
                        entry["pg_enum_values"] = list(type_obj.enums)
                        entry["pg_enum_name"] = type_obj.name
                    if getattr(type_obj, "timezone", False):
                        entry["pg_timestamptz"] = True
                    type_str_upper = str(type_obj).upper()
                    if type_str_upper == "TSVECTOR":
                        config = getattr(type_obj, "regconfig", None)
                        pg_type_entry: dict[str, Any] = {"kind": "tsvector"}
                        if config:
                            pg_type_entry["config"] = str(config)
                        entry["pg_type"] = pg_type_entry
                    elif type_str_upper.endswith("RANGE"):
                        entry["pg_type"] = {"kind": "range"}
                    if col_name in fk_options_map:
                        entry["fk_options"] = fk_options_map[col_name]

                columns_info.append(entry)

            fk_options_map: dict[str, dict[str, Any]] = {}
            for fk in foreign_keys_raw:
                options = fk.get("options", {})
                if options:
                    for c in fk.get("constrained_columns", []):
                        fk_options_map[c] = options

            pg_meta: dict[str, Any] | None = None
            if actual_dialect == "postgresql":
                pg_meta, column_meta = _extract_postgresql_meta(
                    inspector,
                    connection,
                    table_name,
                    raw_columns,
                    indexes_info,
                    checks_info,
                    unique_constraints,
                )
                for col in columns_info:
                    if col["name"] in column_meta:
                        meta = dict(column_meta[col["name"]])
                        comment = meta.pop("comment", None)
                        if comment is not None:
                            col["comment"] = comment
                        if meta:
                            col["pg_meta"] = meta

            ch_options: dict = {}
            if actual_dialect == "clickhouse" and clickhouse_engines:
                ch_options = _extract_ch_meta(connection, table_name)
                # Merge column CH metadata into columns_info
                ch_columns_map: dict[str, dict] = {}
                for ch_col in ch_options.get("columns", []):
                    ch_columns_map[ch_col["name"]] = ch_col
                for col_entry in columns_info:
                    cname = col_entry["name"]
                    if cname in ch_columns_map:
                        ch_col = ch_columns_map[cname]
                        if ch_col.get("ch_meta"):
                            col_entry["ch_meta"] = ch_col["ch_meta"]
                        if ch_col.get("comment"):
                            col_entry["comment"] = col_entry.get("comment") or ch_col["comment"]
                # Mark primary key columns from CH metadata for ORM compatibility
                ch_pk_cols = set()
                for key in ("ch_primary_key", "ch_order_by"):
                    pk_list = ch_options.get(key, [])
                    if pk_list:
                        if isinstance(pk_list, list):
                            ch_pk_cols.update(pk_list)
                        else:
                            ch_pk_cols.add(pk_list)
                if ch_pk_cols:
                    for col_entry in columns_info:
                        if col_entry["name"] in ch_pk_cols:
                            col_entry["primary_key"] = True
                elif actual_dialect == "clickhouse":
                    # CH tables may have no PK at all (MV, dict). Use first col
                    # as PK for SQLAlchemy ORM compatibility.
                    for col_entry in columns_info:
                        col_entry["primary_key"] = True
                        break
                # Remove raw columns list from options (already merged above)
                ch_options.pop("columns", None)

            tables_data.append({
                "name": table_name,
                "columns": columns_info,
                "clickhouse_options": ch_options if ch_options else None,
                "object_type": ch_options.get("ch_object_type", "table") if ch_options else "table",
                "dialect": actual_dialect,
                "pg_meta": pg_meta,
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
                has_engine = bool(t["clickhouse_options"].get("ch_engine") or t["clickhouse_options"].get("ch_engine_raw"))
                if not has_engine:
                    console.print(
                        f"  WARNING: ClickHouse engine metadata for '{t['name']}' may be incomplete.",
                        style="yellow",
                    )


def _clean_engine_full(engine_full: str) -> str:
    """Strip DDL clauses (ORDER BY, PARTITION BY, etc.) from engine_full,
    keeping only the engine name and its direct arguments (e.g. 'MergeTree'
    or 'ReplacingMergeTree(version)')."""
    engine_full = engine_full.strip()
    # Find the engine name boundary
    # Engine name is alphanumeric/underscore chars at the start
    name_end = 0
    for ch in engine_full:
        if ch.isalnum() or ch == '_':
            name_end += 1
        else:
            break
    if name_end == 0:
        return engine_full
    # Check if engine has parenthesized arguments directly after name
    rest = engine_full[name_end:]
    if rest.startswith("("):
        depth = 1
        for i, ch in enumerate(rest[1:], start=1):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = name_end + i + 1
                    return engine_full[:end]
        # unbalanced parens — return as-is
        return engine_full
    # No args: engine name only
    return engine_full[:name_end]


def _extract_ch_meta(connection, table_name: str) -> dict:
    from sqlalchemy import text

    tables_result = connection.execute(
        text(
            "SELECT engine, engine_full, sorting_key, primary_key, partition_key, "
            "sampling_key, create_table_query "
            "FROM system.tables WHERE database = currentDatabase() AND name = :name"
        ),
        parameters={"name": table_name},
    )
    row = tables_result.fetchone()
    if not row:
        return {}

    from dbwarden.engine.safety import (
        _parse_tuple_expression,
        _clean_expression,
        _parse_ttl_expressions,
        _parse_projection_queries,
        _parse_mv_query,
        _parse_zookeeper_path,
        _parse_replica_name,
    )
    from dbwarden.schema.engine import ChEngineSpec

    options: dict = {}
    engine = getattr(row, "engine", "") or ""
    engine_full = getattr(row, "engine_full", "") or ""
    create_query = getattr(row, "create_table_query", "") or ""

    # Build ch_engine_raw for ChEngineSpec emission
    if engine_full:
        options["ch_engine_raw"] = ChEngineSpec.from_engine_string(
            _clean_engine_full(engine_full)
        )
    elif engine:
        options["ch_engine_raw"] = ChEngineSpec.from_engine_string(engine)
    options["ch_engine"] = engine

    sorting_key = _parse_tuple_expression(getattr(row, "sorting_key", None))
    if sorting_key:
        options["ch_order_by"] = sorting_key if isinstance(sorting_key, list) else [sorting_key]
    primary_key = _parse_tuple_expression(getattr(row, "primary_key", None))
    if primary_key:
        options["ch_primary_key"] = primary_key if isinstance(primary_key, list) else [primary_key]
    partition_key = _clean_expression(getattr(row, "partition_key", None))
    if partition_key:
        options["ch_partition_by"] = partition_key
    sampling_key = _clean_expression(getattr(row, "sampling_key", None))
    if sampling_key:
        options["ch_sample_by"] = sampling_key

    ttl = _parse_ttl_expressions(create_query)
    if ttl:
        options["ch_ttl"] = ttl
    projections = _parse_projection_queries(create_query)
    if projections:
        options["ch_projections"] = projections
    mv_query = _parse_mv_query(create_query)
    if mv_query:
        options["ch_select_statement"] = mv_query
        options["ch_object_type"] = "materialized_view"
    zk_path = _parse_zookeeper_path(create_query, engine)
    if zk_path:
        options["ch_zookeeper_path"] = zk_path
    replica = _parse_replica_name(create_query, engine)
    if replica:
        options["ch_replica_name"] = replica

    if engine.upper() == "DICTIONARY":
        options["ch_dictionary"] = True
        options["ch_object_type"] = "dictionary"

    if create_query.strip().upper().startswith("CREATE MATERIALIZED VIEW"):
        options["ch_object_type"] = "materialized_view"

    # Parse SETTINGS, dict options, MV TO table from CREATE TABLE query
    from dbwarden.engine.snapshot import (
        _parse_clickhouse_settings,
        _parse_clickhouse_dict_layout,
        _parse_clickhouse_dict_source,
        _parse_clickhouse_dict_lifetime,
        _parse_clickhouse_dict_primary_key,
        _parse_clickhouse_mv_to_table,
    )
    settings = _parse_clickhouse_settings(create_query)
    if settings:
        options["ch_settings"] = settings

    if engine.upper() == "DICTIONARY":
        layout = _parse_clickhouse_dict_layout(create_query)
        if layout:
            options["ch_dict_layout"] = layout
        source = _parse_clickhouse_dict_source(create_query)
        if source:
            options["ch_dict_source"] = source
        lifetime = _parse_clickhouse_dict_lifetime(create_query)
        if lifetime:
            options["ch_dict_lifetime"] = lifetime
        dict_pk = _parse_clickhouse_dict_primary_key(create_query)
        if dict_pk:
            options["ch_dict_primary_key"] = dict_pk

    if options.get("ch_object_type") == "materialized_view":
        to_table = _parse_clickhouse_mv_to_table(create_query)
        if to_table:
            options["ch_to_table"] = to_table

    # --- Column metadata ---
    columns_result = connection.execute(
        text(
            "SELECT name, type, default_kind, default_expression, compression_codec, "
            "comment, is_in_primary_key, is_in_sorting_key "
            "FROM system.columns "
            "WHERE database = currentDatabase() AND table = :tname "
            "ORDER BY position ASC"
        ),
        parameters={"tname": table_name},
    )
    ch_columns: list[dict] = []
    for c in columns_result.fetchall():
        cname = getattr(c, "name", "")
        raw_type = getattr(c, "type", "") or ""
        default_kind = getattr(c, "default_kind", None) or None
        default_expr = getattr(c, "default_expression", None) or None
        codec_expr = getattr(c, "compression_codec", None) or None
        col_comment = getattr(c, "comment", None) or None

        ch_nullable = raw_type.startswith("Nullable(")
        ch_low_cardinality = raw_type.startswith("LowCardinality(")

        ch_materialized = None
        ch_alias = None
        if default_kind == "MATERIALIZED":
            ch_materialized = default_expr
        elif default_kind == "ALIAS":
            ch_alias = default_expr

        codec = _strip_codec_wrapper(codec_expr) if codec_expr else None

        ch_col: dict = {
            "name": cname,
            "ch_meta": {
                "ch_codec": codec,
                "ch_default_expression": default_expr if default_kind == "DEFAULT" else None,
                "ch_materialized": ch_materialized,
                "ch_alias": ch_alias,
                "ch_low_cardinality": ch_low_cardinality,
                "ch_nullable": ch_nullable,
                "ch_type": raw_type.strip(),
            },
        }
        if col_comment:
            ch_col["comment"] = col_comment
        ch_columns.append(ch_col)

    if ch_columns:
        options["columns"] = ch_columns

    # --- Skip indexes ---
    indices_result = connection.execute(
        text(
            "SELECT name, type, expr, granularity "
            "FROM system.data_skipping_indices "
            "WHERE database = currentDatabase() AND table = :tname"
        ),
        parameters={"tname": table_name},
    )
    skip_indexes: list[dict] = []
    for idx in indices_result.fetchall():
        skip_indexes.append({
            "name": getattr(idx, "name", ""),
            "columns": [getattr(idx, "expr", "")],
            "clickhouse_type": getattr(idx, "type", ""),
            "clickhouse_granularity": getattr(idx, "granularity", 1),
        })
    if skip_indexes:
        options["indexes"] = skip_indexes

    return options
