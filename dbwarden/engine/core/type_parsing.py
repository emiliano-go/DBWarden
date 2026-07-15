from __future__ import annotations

import re
from typing import Any


_TYPE_MAP: dict[str, str] = {
    "INTEGER": "Integer",
    "BIGINT": "BigInteger",
    "SMALLINT": "SmallInteger",
    "VARCHAR": "String",
    "CHAR": "String",
    "TEXT": "Text",
    "BOOLEAN": "Boolean",
    "FLOAT": "Float",
    "REAL": "Float",
    "DOUBLE": "Float",
    "DECIMAL": "Numeric",
    "NUMERIC": "Numeric",
    "DATE": "Date",
    "DATETIME": "DateTime",
    "TIMESTAMP": "DateTime",
    "TIME": "Time",
    "BLOB": "LargeBinary",
    "BYTEA": "LargeBinary",
    "BINARY": "LargeBinary",
    "JSON": "JSON",
    "UUID": "String(36)",
    "ENUM": "Enum",
    "SERIAL": "Integer",
    "BIGSERIAL": "BigInteger",
    "TINYINT": "SmallInteger",
}

_CLICKHOUSE_MAP: dict[str, str] = {
    "Int8": "SmallInteger",
    "Int16": "SmallInteger",
    "Int32": "Integer",
    "Int64": "BigInteger",
    "UInt8": "SmallInteger",
    "UInt16": "Integer",
    "UInt32": "BigInteger",
    "UInt64": "BigInteger",
    "Float32": "Float",
    "Float64": "Float",
    "String": "String",
    "FixedString": "String",
    "Date": "Date",
    "DateTime": "DateTime",
    "DateTime64": "DateTime",
    "UUID": "String(36)",
    "JSON": "JSON",
}


def _parse_type(raw: str, dialect: str | None = None) -> str:
    raw_stripped = raw.strip()
    upper = raw_stripped.upper()

    if dialect == "postgresql":
        if upper == "JSONB":
            return "JSONB"
        if upper == "UUID":
            return "UUID(as_uuid=True)"
        if upper.endswith("[]"):
            inner = _parse_type(raw_stripped[:-2], dialect)
            return f"ARRAY({inner})"

    is_nullable = upper.startswith("NULLABLE(")
    if is_nullable:
        inner = raw_stripped[9:-1].strip()
        inner_type = _parse_type(inner, dialect)
        return inner_type

    if upper.startswith("LOWCARDINALITY("):
        inner = raw_stripped[15:-1].strip()
        return _parse_type(inner, dialect)

    if upper.startswith("ARRAY("):
        inner = raw_stripped[6:-1].strip()
        inner_type = _parse_type(inner, dialect)
        return f"ARRAY({inner_type})"

    if upper.startswith("MAP("):
        return "JSON"

    if upper.startswith("ENUM"):
        match = re.match(r"ENUM\((.*)\)$", raw_stripped, re.IGNORECASE)
        if match:
            return f"Enum({match.group(1)})"
        return "Enum"

    if upper.startswith("DECIMAL") or upper.startswith("NUMERIC"):
        match = re.match(r"(DECIMAL|NUMERIC)\((\d+),\s*(\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"Numeric(precision={match.group(2)}, scale={match.group(3)})"
        return "Numeric"

    if upper.startswith("VARCHAR"):
        match = re.match(r"VARCHAR\((\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"String(length={match.group(1)})"
        return "String"

    if upper.startswith("CHAR"):
        match = re.match(r"CHAR\((\d+)\)", raw_stripped, re.IGNORECASE)
        if match:
            return f"CHAR(length={match.group(1)})"
        return "CHAR"

    if upper.startswith("FLOAT"):
        return "Float"

    if upper.startswith("DOUBLE"):
        return "Float"

    if upper.startswith("DATETIME"):
        return "DateTime"

    if upper.startswith("TIMESTAMP"):
        return "DateTime"

    if upper.startswith("TINYINT"):
        if upper == "TINYINT(1)":
            return "Boolean"
        return "SmallInteger"

    if upper.startswith("LONGTEXT"):
        return "Text"

    if upper.startswith("MEDIUMTEXT"):
        return "Text"

    if upper.startswith("TINYTEXT"):
        return "Text"

    if upper.startswith("BIGINT"):
        return "BigInteger"

    if upper.startswith("SMALLINT"):
        return "SmallInteger"

    if upper.startswith("SERIAL"):
        return "Integer"

    if upper.startswith("BIGSERIAL"):
        return "BigInteger"

    if dialect and dialect == "clickhouse":
        for ch_key, ch_val in _CLICKHOUSE_MAP.items():
            if raw_stripped.upper().startswith(ch_key.upper()):
                return ch_val

    for t_key, t_val in _TYPE_MAP.items():
        if upper.startswith(t_key):
            return t_val

    if upper.startswith("INT"):
        return "Integer"

    return "String"


def _format_default(default: Any) -> str | None:
    if default is None:
        return None
    raw = str(default).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        raw = raw[1:-1]
    if not raw:
        return None
    upper = raw.upper()
    if upper == "NULL":
        return None
    if upper == "CURRENT_TIMESTAMP":
        return "func.now()"
    if upper == "CURRENT_DATE":
        return "func.current_date()"
    if upper == "CURRENT_TIME":
        return "func.current_time()"
    if upper in ("TRUE", "FALSE"):
        return raw.capitalize()
    if upper in ("1", "0"):
        return raw
    if re.match(r"^\d+(\.\d+)?$", raw):
        return raw
    return repr(raw)
