from __future__ import annotations

from typing import Any

from sqlalchemy import text

from dbwarden.databases.clickhouse.engine import ChEngineSpec

from dbwarden.engine.backends.clickhouse.parse import (
    parse_dict_layout as _parse_clickhouse_dict_layout,
    parse_dict_lifetime as _parse_clickhouse_dict_lifetime,
    parse_dict_primary_key as _parse_clickhouse_dict_primary_key,
    parse_dict_source as _parse_clickhouse_dict_source,
    parse_mv_query as _parse_clickhouse_mv_query,
    parse_mv_to_table as _parse_clickhouse_mv_to_table,
    parse_projection_queries as _parse_clickhouse_projection_queries,
    parse_replica_name as _parse_clickhouse_replica_name,
    parse_settings as _parse_clickhouse_settings,
    parse_ttl_expressions as _parse_clickhouse_ttl_expressions,
    parse_tuple_or_list as _clickhouse_tuple_or_list,
    parse_zookeeper_path as _parse_clickhouse_zookeeper_path,
)

from .ch_utils import _clean_clickhouse_expression, _pick_clickhouse_codec, _serialize_clickhouse_engine


def _extract_clickhouse_schema_snapshot(connection: Any, db_name: str) -> dict[str, Any]:
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
