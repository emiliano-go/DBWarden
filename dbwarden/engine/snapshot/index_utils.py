from __future__ import annotations

from typing import Any

from dbwarden.engine.core.models import IndexInfo
from dbwarden.engine.core.statement_order import MigrationStatement, StatementOrder

from .type_normalize import _normalize_index_col


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


def _rename_table_sql(intent: Any, backend: str) -> MigrationStatement:
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
