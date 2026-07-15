from __future__ import annotations

from typing import Any

from dbwarden.engine.backends.mysql.render import (
    append_mysql_column_attrs,
    render_mysql_column_type,
)


def render_mariadb_column_type(type_str: str, meta: dict[str, Any]) -> str:
    return render_mysql_column_type(type_str, meta)


def append_mariadb_column_attrs(sql: str, meta: dict[str, Any]) -> str:
    return append_mysql_column_attrs(sql, meta)
