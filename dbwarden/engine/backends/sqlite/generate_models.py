from __future__ import annotations

from typing import Any


def resolve_sqlite_imports(columns: list[dict]) -> set[str]:
    imports: set[str] = set()
    return imports


def extract_sqlite_meta(
    connection, table_name: str,
    indexes: list[dict] | None = None,
    checks: list[dict] | None = None,
    uniques: list[dict] | None = None,
    raw_columns: list[dict] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    from dbwarden.engine.backends.sqlite.extract import (
        extract_sqlite_column_meta,
        extract_sqlite_table_meta,
    )

    table_meta = extract_sqlite_table_meta(connection, table_name)
    column_meta = extract_sqlite_column_meta(None, connection, table_name, raw_columns or [])
    return table_meta, column_meta


def _render_sqlite_meta(columns: list[dict], sq_meta: dict | None = None) -> list[str]:
    if not sq_meta and not any(col.get("sq_meta") for col in columns):
        return []

    from dbwarden.engine.shared.format_utils import _format_meta_value

    lines = ["    class Meta(SqTableMeta):"]
    sq_meta = sq_meta or {}
    for key, value in sq_meta.items():
        if key == "comment":
            lines.append(f"        comment = {value!r}")
        else:
            rendered = _format_meta_value(value)
            if rendered:
                lines.append(f"        {key} = {rendered[0].strip()}")

    for col in columns:
        field_meta: dict[str, Any] = {}
        if col.get("comment"):
            field_meta["comment"] = col["comment"]
        field_meta.update(col.get("sq_meta") or {})
        if not field_meta:
            continue
        lines.append("")
        lines.append(f"        class {col['name']}(SqColumnMeta):")
        comment_val = field_meta.pop("comment", None)
        if comment_val is not None:
            lines.append(f"            comment = {comment_val!r}")
        for key, value in field_meta.items():
            rendered = _format_meta_value(value)
            if rendered:
                lines.append(f"            {key} = {rendered[0].strip()}")

    return lines
