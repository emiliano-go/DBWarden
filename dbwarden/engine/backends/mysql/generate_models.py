from __future__ import annotations

import re
from typing import Any

from dbwarden.engine.shared.format_utils import _format_meta_value


def resolve_mysql_imports(columns: list[dict]) -> set[str]:
    imports: set[str] = set()
    for col in columns:
        raw_type = str(col.get("type", "")).upper()
        if raw_type.startswith("YEAR"):
            imports.add("Integer")
    return imports


def extract_mysql_meta(
    connection, table_name: str,
    indexes: list[dict] | None = None,
    checks: list[dict] | None = None,
    uniques: list[dict] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    from sqlalchemy import text

    table_meta: dict[str, Any] = {}
    column_meta: dict[str, dict[str, Any]] = {}

    try:
        row = connection.execute(
            text(
                "SELECT ENGINE, TABLE_COLLATION, AUTO_INCREMENT, ROW_FORMAT, TABLE_COMMENT "
                "FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
            ),
            {"t": table_name},
        ).fetchone()
        if row:
            if row[0]:
                table_meta["my_engine"] = row[0]
            if row[1]:
                table_meta["my_collate"] = row[1]
                charset = str(row[1]).split("_", 1)[0]
                if charset:
                    table_meta["my_charset"] = charset
            if row[2] is not None:
                table_meta["my_auto_increment"] = int(row[2])
            if row[3]:
                table_meta["my_row_format"] = row[3]
            if row[4]:
                table_meta["comment"] = row[4]
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    try:
        rows = connection.execute(
            text(
                "SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_SET_NAME, COLLATION_NAME, EXTRA, COLUMN_COMMENT "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "ORDER BY ORDINAL_POSITION"
            ),
            {"t": table_name},
        ).fetchall()
        for row in rows:
            meta: dict[str, Any] = {}
            column_type = str(row[1] or "")
            if "unsigned" in column_type.lower():
                meta["my_unsigned"] = True
            if row[2]:
                meta["my_charset"] = row[2]
            if row[3]:
                meta["my_collate"] = row[3]
            extra = str(row[4] or "")
            on_update_match = re.search(r"on update\s+(.+)$", extra, re.IGNORECASE)
            if on_update_match:
                meta["my_on_update"] = on_update_match.group(1).strip()
            if row[5]:
                meta["comment"] = row[5]
            if meta:
                column_meta[row[0]] = meta
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass

    if indexes:
        my_indexes: list[dict[str, Any]] = []
        for idx in indexes:
            entry: dict[str, Any] = {
                "name": idx.get("name"),
                "columns": list(idx.get("column_names", [])),
                "unique": bool(idx.get("unique", False)),
            }
            dialect_options = idx.get("dialect_options", {})
            for k in ("mysql_using", "mariadb_using"):
                val = dialect_options.get(k)
                if val:
                    entry["using"] = val
                    break
            if "using" not in entry:
                entry["using"] = "btree"
            my_indexes.append(entry)
        if my_indexes:
            table_meta["my_indexes"] = my_indexes

    if checks:
        table_meta["my_checks"] = [
            {"name": ck.get("name"), "expression": ck.get("sqltext", "")}
            for ck in checks
        ]

    if uniques:
        table_meta["my_uniques"] = [
            {"name": uq.get("name"), "columns": list(uq.get("column_names", []))}
            for uq in uniques
        ]

    return table_meta, column_meta


def _render_mysql_meta(columns: list[dict], my_meta: dict | None = None) -> list[str]:
    if not my_meta and not any(col.get("my_meta") or col.get("comment") for col in columns):
        return []

    lines = ["    class Meta(MyTableMeta):"]
    my_meta = my_meta or {}
    for key, value in my_meta.items():
        if key == "comment":
            lines.append(f"        comment = {value!r}")
        else:
            rendered = _format_meta_value(value)
            if len(rendered) == 1:
                lines.append(f"        {key} = {rendered[0].strip()}")
            else:
                lines.append(f"        {key} = {rendered[0].strip()}")
                lines.extend(rendered[1:])

    flat_to_spec: dict[str, str] = {
        "my_charset": "charset",
        "my_collate": "collate",
        "my_unsigned": "unsigned",
        "my_on_update": "on_update",
    }

    for col in columns:
        field_meta: dict[str, Any] = {}
        if col.get("comment"):
            field_meta["comment"] = col["comment"]
        field_meta.update(col.get("my_meta") or {})
        if not field_meta:
            continue
        lines.append("")
        lines.append(f"        class {col['name']}(MyColumnMeta):")
        comment_val = field_meta.pop("comment", None)
        if comment_val is not None:
            lines.append(f"            comment = {comment_val!r}")
        my_kwargs = {}
        for flat_key, spec_key in flat_to_spec.items():
            if flat_key in field_meta:
                my_kwargs[spec_key] = field_meta[flat_key]
        if my_kwargs:
            kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in my_kwargs.items())
            lines.append(f"            my = my.field({kwargs_repr})")

    return lines
