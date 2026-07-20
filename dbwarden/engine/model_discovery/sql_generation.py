from dbwarden.engine.backends.mysql.render import (
    append_mysql_column_attrs as _append_mysql_column_attrs,
    render_mysql_column_type as _render_mysql_column_type,
)
from dbwarden.engine.backends.postgresql.render import (
    _build_create_policy_sql,
    _build_grant_sql,
    _quote_pg,
    _render_postgres_column_type,
    generate_create_view_sql,
)
from dbwarden.engine.backends.clickhouse.render import (
    _generate_clickhouse_materialized_view_sql,
    _render_clickhouse_projections,
    _render_clickhouse_table_suffix,
    generate_create_dictionary_sql,
)
from dbwarden.engine.core.models import ModelTable
from . import type_mapping as _type_mapping


def _get_backend_name(db_name=None):
    return _type_mapping._get_backend_name(db_name)

def _validate_identifier(name, field="identifier"):
    return _type_mapping._validate_identifier(name, field)


def _qualified_name(name: str, schema: str | None) -> str:
    if schema:
        return f"{schema}.{name}"
    return name


def generate_add_column_sql(
    table_name: str, column: ModelTable, db_name: str | None = None,
    schema: str | None = None,
) -> str:
    _validate_identifier(table_name, "table_name")
    _validate_identifier(column.name, "column_name")

    backend = _get_backend_name(db_name)
    if backend == "clickhouse":
        col_type = column.ch_meta.get("ch_type", column.type)
    elif backend in ("mysql", "mariadb"):
        col_type = _render_mysql_column_type(column.type, column.my_meta)
    elif backend == "postgresql":
        col_type = _render_postgres_column_type(column)
    else:
        col_type = column.type
    is_serial = (
        column.type.upper() in ("SERIAL", "BIGSERIAL")
        if backend == "postgresql"
        else False
    )

    nullable_sql = "" if column.nullable or is_serial or backend == "clickhouse" else "NOT NULL"
    default_sql = f" DEFAULT {column.default}" if column.default and backend != "clickhouse" else ""
    fk_sql = ""
    if column.foreign_key and backend != "postgresql":
        fk_sql = f" REFERENCES {column.foreign_key}"
        if column.fk_on_delete and column.fk_on_delete != "NO ACTION":
            fk_sql += f" ON DELETE {column.fk_on_delete}"
        if column.fk_on_update and column.fk_on_update != "NO ACTION":
            fk_sql += f" ON UPDATE {column.fk_on_update}"
    if backend == "postgresql":
        qtable = _quote_pg(table_name)
        qschema = _quote_pg(schema) if schema else None
        qname = _qualified_name(qtable, qschema)
        col_name = _quote_pg(column.name)
    else:
        qname = _qualified_name(table_name, schema)
        col_name = column.name
    sql = f"ALTER TABLE {qname} ADD COLUMN {col_name} {col_type}"
    if nullable_sql:
        sql += f" {nullable_sql}"
    if default_sql:
        sql += default_sql
    if backend == "clickhouse":
        ch_meta = column.ch_meta
        for key, keyword in (
            ("ch_default_expression", "DEFAULT"),
            ("ch_materialized", "MATERIALIZED"),
            ("ch_alias", "ALIAS"),
            ("ch_ephemeral", "EPHEMERAL"),
        ):
            val = ch_meta.get(key)
            if val:
                sql += f" {keyword} {val}"
        ch_codec = column.codec or ch_meta.get("ch_codec")
        if ch_codec:
            sql += f" CODEC({ch_codec})"
        ch_ttl = ch_meta.get("ch_ttl")
        if ch_ttl:
            sql += f" TTL {ch_ttl}"
        if column.comment:
            sql += f" COMMENT '{column.comment.replace(chr(39), chr(39) + chr(39))}'"
    if backend in ("mysql", "mariadb"):
        sql = _append_mysql_column_attrs(sql, column.my_meta)
    if fk_sql:
        sql += fk_sql
    return sql


def generate_create_table_sql(table: ModelTable, db_name: str | None = None) -> str:
    backend = _get_backend_name(db_name)

    if backend == "clickhouse" and table.object_type == "dictionary":
        return generate_create_dictionary_sql(table)

    column_defs = []

    for col in table.columns:
        if backend == "clickhouse":
            col_type = col.ch_meta.get("ch_type", col.type)
        elif backend in ("mysql", "mariadb"):
            col_type = _render_mysql_column_type(col.type, col.my_meta)
        elif backend == "postgresql":
            col_type = _render_postgres_column_type(col)
        else:
            col_type = col.type
        col_name = _quote_pg(col.name) if backend == "postgresql" else col.name
        col_def = f"    {col_name} {col_type}"
        is_serial = (
            col.type.upper() in ("SERIAL", "BIGSERIAL")
            if backend == "postgresql"
            else False
        )

        if not col.nullable and not is_serial and backend != "clickhouse":
            col_def += " NOT NULL"
        if backend != "clickhouse" and col.primary_key:
            col_def += " PRIMARY KEY"
        elif col.unique:
            col_def += " UNIQUE"
        if backend != "clickhouse" and col.default and not is_serial:
            col_def += f" DEFAULT {col.default}"
        if backend == "clickhouse":
            for key, keyword in (
                ("ch_default_expression", "DEFAULT"),
                ("ch_materialized", "MATERIALIZED"),
                ("ch_alias", "ALIAS"),
                ("ch_ephemeral", "EPHEMERAL"),
            ):
                val = col.ch_meta.get(key)
                if val:
                    col_def += f" {keyword} {val}"
        if backend in ("mysql", "mariadb"):
            col_def = _append_mysql_column_attrs(col_def, col.my_meta)
        if col.foreign_key and backend != "postgresql":
            col_def += f" REFERENCES {col.foreign_key}"
            if col.fk_on_delete and col.fk_on_delete != "NO ACTION":
                col_def += f" ON DELETE {col.fk_on_delete}"
            if col.fk_on_update and col.fk_on_update != "NO ACTION":
                col_def += f" ON UPDATE {col.fk_on_update}"
        if backend == "clickhouse":
            if col.codec:
                col_def += f" CODEC({col.codec})"
            ch_ttl = col.ch_meta.get("ch_ttl")
            if ch_ttl:
                col_def += f" TTL {ch_ttl}"
            if col.comment:
                col_def += f" COMMENT '{col.comment.replace(chr(39), chr(39) + chr(39))}'"
        column_defs.append(col_def)

    if backend == "clickhouse":
        column_defs.extend(f"    {projection_sql}" for projection_sql in _render_clickhouse_projections(table))

    columns_sql = ",\n".join(column_defs)
    if backend == "postgresql":
        qtable = _quote_pg(table.name)
        qschema = _quote_pg(table.schema) if table.schema else None
    else:
        qtable = table.name
        qschema = table.schema
    qname = _qualified_name(qtable, qschema)
    if backend == "clickhouse" and table.object_type == "materialized_view":
        sql = _generate_clickhouse_materialized_view_sql(table, columns_sql)
    elif backend == "postgresql" and table.object_type in ("view", "materialized_view"):
        return generate_create_view_sql(table, qname)
    else:
        unlogged = "UNLOGGED " if table.pg_table and table.pg_table.get("pg_unlogged") else ""
        sql = f"CREATE {unlogged}TABLE IF NOT EXISTS {qname} (\n{columns_sql}\n)"
    if backend == "clickhouse":
        if table.object_type == "table":
            sql += _render_clickhouse_table_suffix(table)
        if table.comment:
            sql += f" COMMENT '{table.comment.replace(chr(39), chr(39) + chr(39))}'"
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
            quoted_cols = ", ".join(_quote_pg(c) for c in columns)
            sql += f"\nPARTITION BY {strategy} ({quoted_cols})"
        pg_inherits = table.pg_table.get("pg_inherits")
        if pg_inherits:
            parent = _quote_pg(pg_inherits) if isinstance(pg_inherits, str) else ", ".join(_quote_pg(p) for p in pg_inherits)
            sql += f"\nINHERITS ({parent})"
        pg_tablespace = table.pg_table.get("pg_tablespace")
        if pg_tablespace:
            sql += f"\nTABLESPACE {pg_tablespace}"
    if backend == "postgresql" and table.comment:
        sql += f";\nCOMMENT ON TABLE {qname} IS '{table.comment.replace(chr(39), chr(39) + chr(39))}';"
    if backend == "postgresql":
        pg_rls = table.pg_table.get("pg_rls", False)
        pg_rls_force = table.pg_table.get("pg_rls_force", False)
        pg_suffix = ""
        if pg_rls:
            pg_suffix += f"\nALTER TABLE {qname} ENABLE ROW LEVEL SECURITY;"
        if pg_rls_force:
            pg_suffix += f"\nALTER TABLE {qname} FORCE ROW LEVEL SECURITY;"
        for policy in table.pg_policies:
            pg_suffix += f"\n{_build_create_policy_sql(policy, qname)}"
        for grant_entry in table.pg_grants:
            pg_suffix += f"\n{_build_grant_sql(grant_entry, qname)}"
        if pg_suffix:
            if not sql.endswith(";"):
                sql += ";"
            sql += pg_suffix
    if not sql.endswith(";"):
        sql += ";"
    return sql


def generate_drop_table_sql(table_name: str, schema: str | None = None) -> str:
    _validate_identifier(table_name, "table_name")
    qname = _qualified_name(table_name, schema)
    return f"DROP TABLE {qname}"


def generate_drop_object_sql(table: ModelTable) -> str:
    qname = _qualified_name(table.name, table.schema)
    if table.object_type == "materialized_view" and table.pg_view_materialized:
        return f"DROP MATERIALIZED VIEW IF EXISTS {qname}"
    if table.object_type in ("view", "materialized_view"):
        return f"DROP VIEW IF EXISTS {qname}"
    if table.object_type == "dictionary":
        return f"DROP DICTIONARY {qname}"
    return generate_drop_table_sql(table.name, table.schema)
