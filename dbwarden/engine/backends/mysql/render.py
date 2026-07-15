from __future__ import annotations

from typing import Any


def render_mysql_column_type(type_str: str, meta: dict[str, Any]) -> str:
    rendered = type_str
    if meta.get("my_unsigned") and "UNSIGNED" not in rendered.upper():
        rendered = f"{rendered} UNSIGNED"
    return rendered


def append_mysql_column_attrs(sql: str, meta: dict[str, Any]) -> str:
    if meta.get("my_charset"):
        sql += f" CHARACTER SET {meta['my_charset']}"
    if meta.get("my_collate"):
        sql += f" COLLATE {meta['my_collate']}"
    if meta.get("my_on_update"):
        sql += f" ON UPDATE {meta['my_on_update']}"
    return sql
