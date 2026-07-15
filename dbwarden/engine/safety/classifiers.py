from __future__ import annotations

from enum import Enum
from typing import Any


class Safety(str, Enum):
    SAFE = "SAFE"
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


def _snapshot_column_type_signature(snapshot_column: dict[str, Any]) -> dict[str, Any]:
    extra_keys = {"length", "precision", "scale", "pg_type", "enum_name"}
    if not any(key in snapshot_column for key in extra_keys):
        from dbwarden.engine.snapshot.type_normalize import normalize_type

        return normalize_type(str(snapshot_column.get("type", "")))

    sig: dict[str, Any] = {"type": snapshot_column.get("type")}
    for key in ("length", "precision", "scale", "pg_type", "enum_name"):
        if key in snapshot_column:
            sig[key] = snapshot_column[key]
    return sig
