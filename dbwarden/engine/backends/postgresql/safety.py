from __future__ import annotations

from typing import Any


def classify_pg_type_change(from_type: dict[str, Any], to_type: dict[str, Any]) -> str:
    from_kind = from_type.get("kind") or from_type.get("type")
    to_kind = to_type.get("kind") or to_type.get("type")

    if from_kind == "varchar" and to_kind == "varchar":
        fl, tl = from_type.get("length"), to_type.get("length")
        if fl is None or tl is None or tl >= fl:
            return "SAFE"
        return "CRITICAL"
    if from_kind == "integer" and to_kind == "biginteger":
        return "SAFE"
    if from_kind == "varchar" and to_kind == "text":
        return "SAFE"
    if from_kind == "json" and to_kind == "jsonb":
        return "SAFE"
    if {from_kind, to_kind} == {"timestamp", "timestamptz"}:
        return "WARN"
    if from_kind == "numeric":
        fp = from_type.get("precision")
        tp = to_type.get("precision")
        if fp and tp and tp < fp:
            return "CRITICAL"
    if from_kind != to_kind:
        return "CRITICAL"
    return "SAFE"


def classify_enum_change(from_values: list[str], to_values: list[str]) -> str:
    if set(from_values) - set(to_values):
        return "CRITICAL"
    if set(to_values) - set(from_values):
        return "WARN"
    return "SAFE"
