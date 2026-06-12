from __future__ import annotations

from typing import Any


def partition_by_range(column: str, *, interval: str | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {"method": "range", "column": column}
    if interval is not None:
        d["interval"] = interval
    return d


def partition_by_list(column: str) -> dict[str, Any]:
    return {"method": "list", "column": column}


def partition_by_hash(column: str, partitions: int) -> dict[str, Any]:
    return {"method": "hash", "column": column, "partitions": partitions}
