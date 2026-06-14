from __future__ import annotations

from typing import Any


def skip_index(
    name: str,
    columns: list[str],
    type: str,
    *,
    granularity: int = 1,
    expr: str | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "name": name,
        "columns": list(columns),
        "clickhouse_type": type,
        "clickhouse_granularity": granularity,
    }
    if expr is not None:
        d["expr"] = expr
    return d
