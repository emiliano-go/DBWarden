from __future__ import annotations

from typing import Any


def extract_sqlite_column_meta(
    inspector,
    connection,
    table_name: str,
    raw_columns: list[dict],
) -> dict[str, dict[str, Any]]:
    """Extract SQLite-specific column metadata (generated columns, etc.)."""
    column_meta: dict[str, dict[str, Any]] = {}
    for col in raw_columns:
        meta: dict[str, Any] = {}
        default = col.get("default")
        if default is not None:
            from dbwarden.engine.sqlite_translation import translate_default_to_sqlite
            translated = translate_default_to_sqlite(str(default))
            if translated != str(default):
                meta["sq_default_translated"] = translated
        dialect_options = col.get("dialect_options", {})
        if dialect_options:
            generated = dialect_options.get("sqlite_on_conflict")
            if generated:
                meta["sq_on_conflict"] = generated
        if meta:
            column_meta[col["name"]] = meta
    return column_meta


def extract_sqlite_table_meta(
    connection,
    table_name: str,
) -> dict[str, Any]:
    """Extract SQLite-specific table metadata (without_rowid, strict)."""
    table_meta: dict[str, Any] = {}
    try:
        from sqlalchemy import text
        row = connection.execute(
            text(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table_name},
        ).fetchone()
        if row and row[0]:
            sql = str(row[0]).upper()
            if "WITHOUT ROWID" in sql:
                table_meta["sq_without_rowid"] = True
            if "STRICT" in sql:
                table_meta["sq_strict"] = True
    except Exception:
        pass
    return table_meta
