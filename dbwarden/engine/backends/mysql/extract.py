from __future__ import annotations

import re
from typing import Any

_INCOMPLETE_MYSQL_TYPES = re.compile(
    r"^(VARCHAR|CHAR|VARBINARY|BINARY|ENUM|SET)$",
    re.IGNORECASE,
)


def assert_complete_mysql_type(col_type: str) -> None:
    stripped = col_type.strip()
    if _INCOMPLETE_MYSQL_TYPES.match(stripped):
        raise ValueError(
            f"Incomplete MySQL column type '{col_type}' - "
            f"{stripped} requires a length or value list (e.g. {stripped}(255)). "
            f"Check the model column definition."
        )


def normalize_mysql_default(d: Any) -> str | None:
    from dbwarden.engine.snapshot import _normalize_default
    s = _normalize_default(d)
    if s is None or s.upper() == "NULL":
        return None
    upper = s.upper()
    if upper.startswith("CURRENT_TIMESTAMP("):
        s = "CURRENT_TIMESTAMP"
    elif upper.startswith("ON UPDATE CURRENT_TIMESTAMP"):
        s = "CURRENT_TIMESTAMP"
    elif upper.startswith("CURRENT_TIMESTAMP ON UPDATE "):
        s = "CURRENT_TIMESTAMP"
    if len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        s = s[1:-1]
    return s


def normalize_mysql_table_value(key: str, value: Any) -> Any:
    if value is None and key in {"my_auto_increment", "my_row_format"}:
        return None
    if isinstance(value, str) and key in {"my_engine", "my_charset", "my_collate", "my_row_format"}:
        return value.lower()
    return value


def mysql_column_definition_for_meta(
    col_type: str,
    meta: dict[str, Any],
    nullable: bool | None = None,
    default: str | None = None,
    comment: str | None = None,
    autoincrement: bool | None = None,
) -> str:
    assert_complete_mysql_type(col_type)
    definition = col_type
    if meta.get("my_unsigned") and "UNSIGNED" not in definition.upper():
        definition = f"{definition} UNSIGNED"
    if autoincrement:
        definition += " AUTO_INCREMENT"
    if nullable is not None:
        definition += " NOT NULL" if not nullable else " NULL"
    if default is not None:
        definition += f" DEFAULT {default}"
    if comment is not None:
        escaped = comment.replace("'", "''")
        definition += f" COMMENT '{escaped}'"
    if meta.get("my_charset"):
        definition += f" CHARACTER SET {meta['my_charset']}"
    if meta.get("my_collate"):
        definition += f" COLLATE {meta['my_collate']}"
    if meta.get("my_on_update"):
        definition += f" ON UPDATE {meta['my_on_update']}"
    return definition
