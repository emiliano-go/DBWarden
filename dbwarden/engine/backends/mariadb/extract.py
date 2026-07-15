from __future__ import annotations

from typing import Any

from dbwarden.engine.backends.mysql.extract import (
    assert_complete_mysql_type,
    mysql_column_definition_for_meta,
    normalize_mysql_default,
    normalize_mysql_table_value,
)


def assert_complete_mariadb_type(col_type: str) -> None:
    return assert_complete_mysql_type(col_type)


def normalize_mariadb_default(d: Any) -> str | None:
    return normalize_mysql_default(d)


def normalize_mariadb_table_value(key: str, value: Any) -> Any:
    return normalize_mysql_table_value(key, value)


def mariadb_column_definition_for_meta(
    col_type: str,
    meta: dict[str, Any],
    nullable: bool | None = None,
    default: str | None = None,
    comment: str | None = None,
    autoincrement: bool | None = None,
) -> str:
    return mysql_column_definition_for_meta(
        col_type, meta,
        nullable=nullable,
        default=default,
        comment=comment,
        autoincrement=autoincrement,
    )
