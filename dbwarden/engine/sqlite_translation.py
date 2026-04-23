import re


def _fail_or_fallback(
    message: str,
    strict: bool,
    fallback_value: str,
) -> tuple[str, str | None]:
    if strict:
        raise ValueError(message)
    return fallback_value, message


def _normalize_type(type_str: str) -> str:
    return re.sub(r"\s+", " ", type_str.strip()).upper()


def _unwrap_clickhouse_type(type_upper: str) -> str:
    current = type_upper
    while True:
        nullable_match = re.match(r"NULLABLE\((.+)\)$", current)
        if nullable_match:
            current = nullable_match.group(1).strip()
            continue

        low_card_match = re.match(r"LOWCARDINALITY\((.+)\)$", current)
        if low_card_match:
            current = low_card_match.group(1).strip()
            continue

        break

    return current


def translate_type_to_sqlite(
    type_str: str,
    strict: bool = False,
) -> tuple[str, str | None]:
    """Translate backend-specific SQL type to SQLite-compatible type."""
    type_upper = _normalize_type(type_str)
    type_upper = _unwrap_clickhouse_type(type_upper)

    direct_mapping = {
        "UUID": "TEXT",
        "JSON": "TEXT",
        "JSONB": "TEXT",
        "BYTEA": "BLOB",
        "TIMESTAMPTZ": "DATETIME",
        "TIMESTAMP WITH TIME ZONE": "DATETIME",
        "SERIAL": "INTEGER",
        "BIGSERIAL": "INTEGER",
        "BOOL": "BOOLEAN",
        "INT8": "INTEGER",
        "INT16": "INTEGER",
        "INT32": "INTEGER",
        "INT64": "INTEGER",
        "UINT8": "INTEGER",
        "UINT16": "INTEGER",
        "UINT32": "INTEGER",
        "UINT64": "INTEGER",
        "FLOAT32": "REAL",
        "FLOAT64": "REAL",
        "DATETIME64": "DATETIME",
    }

    if type_upper in direct_mapping:
        translated = direct_mapping[type_upper]
        if translated != type_upper:
            return (
                translated,
                f"Translated type '{type_str}' to '{translated}' for SQLite compatibility.",
            )
        return translated, None

    if type_upper.startswith("ARRAY("):
        return _fail_or_fallback(
            f"Type '{type_str}' is not supported by SQLite. Falling back to TEXT.",
            strict,
            "TEXT",
        )

    if type_upper.startswith("DECIMAL(") or type_upper.startswith("NUMERIC("):
        return (
            "NUMERIC",
            f"Translated type '{type_str}' to 'NUMERIC' for SQLite compatibility.",
        )

    if type_upper.startswith("DATETIME64("):
        return (
            "DATETIME",
            f"Translated type '{type_str}' to 'DATETIME' for SQLite compatibility.",
        )

    if type_upper.startswith("FIXEDSTRING("):
        return (
            "TEXT",
            f"Translated type '{type_str}' to 'TEXT' for SQLite compatibility.",
        )

    supported_prefixes = (
        "INTEGER",
        "INT",
        "BIGINT",
        "SMALLINT",
        "VARCHAR",
        "CHAR",
        "TEXT",
        "BOOLEAN",
        "REAL",
        "FLOAT",
        "DOUBLE",
        "DATE",
        "DATETIME",
        "TIMESTAMP",
        "BLOB",
        "NUMERIC",
    )
    if type_upper.startswith(supported_prefixes):
        return type_str, None

    return _fail_or_fallback(
        f"Type '{type_str}' is not supported by SQLite. Falling back to TEXT.",
        strict,
        "TEXT",
    )


def translate_default_to_sqlite(
    default_value: str | None,
    strict: bool = False,
) -> tuple[str | None, str | None]:
    """Translate backend-specific default expression to SQLite-compatible default."""
    if not default_value:
        return None, None

    normalized = default_value.strip().upper()
    if normalized in ("CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME"):
        return default_value, None

    unsupported_patterns = (
        "NOW()",
        "UUID_GENERATE_V4()",
        "GEN_RANDOM_UUID()",
        "NEXTVAL(",
    )
    if any(pattern in normalized for pattern in unsupported_patterns):
        if strict:
            raise ValueError(
                f"Default expression '{default_value}' is not supported by SQLite."
            )
        return None, (
            f"Default expression '{default_value}' is not supported by SQLite and was removed."
        )

    return default_value, None
