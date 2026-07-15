from __future__ import annotations

from typing import Any

from dbwarden.engine.backends.mysql.extract import (
    assert_complete_mysql_type,
    mysql_column_definition_for_meta,
)
from dbwarden.engine.snapshot.utils import (
    _missing_def_placeholder,
    _quote_default_for_sql,
)


def build_mysql_alter_default_sql(
    table: str,
    column: str,
    default: Any,
    col_type: str | None = None,
    nullable: bool | None = None,
    my_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    if col_type:
        assert_complete_mysql_type(col_type)
    if default is not None:
        safe_default = _quote_default_for_sql(str(default))
        if not col_type:
            placeholder = _missing_def_placeholder(backend="mysql")
            upgrade = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {safe_default} {placeholder}"
            rollback = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT {placeholder}"
            return upgrade, rollback
        upgrade_def = mysql_column_definition_for_meta(
            col_type, my_meta or {},
            nullable=nullable, default=safe_default,
        )
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {upgrade_def}"
        rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {_missing_def_placeholder(backend='mysql')}"
    else:
        if not col_type:
            placeholder = _missing_def_placeholder(backend="mysql")
            upgrade = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT {placeholder}"
            rollback = f"-- MANUAL ACTION REQUIRED: ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {placeholder}"
            return upgrade, rollback
        upgrade_def = mysql_column_definition_for_meta(
            col_type, my_meta or {}, nullable=nullable, default=None,
        )
        upgrade = f"ALTER TABLE {table} MODIFY COLUMN {column} {upgrade_def}"
        rollback = f"ALTER TABLE {table} MODIFY COLUMN {column} {_missing_def_placeholder(backend='mysql')}"
    return upgrade, rollback
