from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.schema.index import ChIndexSpec


@dataclass
class ChTableSpec:
    engine: str = "MergeTree"
    order_by: list[str] | None = None
    primary_key: str | list[str] | None = None
    partition_by: str | None = None
    sample_by: str | None = None
    ttl: str | None = None
    settings: dict[str, str] | None = None
    zookeeper_path: str | None = None
    replica_name: str | None = None
    object_type: str = "table"
    select_statement: str | None = None
    to_table: str | None = None


def ch_index(
    name: str,
    columns: list[str],
    *,
    type: str = "bloom_filter",
    granularity: int = 1,
    expr: str | None = None,
) -> ChIndexSpec:
    return ChIndexSpec(
        name=name, columns=columns, type=type,
        granularity=granularity, expr=expr,
    )


__all__ = [
    "ChTableSpec",
    "ChIndexSpec",
    "ch_index",
]
