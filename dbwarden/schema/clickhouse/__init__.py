from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ChIndexSpec:
    """Typed spec for a ClickHouse skip index in ``class Meta``.

    Example::

        from dbwarden import ChIndexSpec

        class Meta(CHTableMeta):
            ch_indexes = [
                ChIndexSpec("ix_payload", ["payload"],
                    type="bloom_filter", granularity=1),
            ]
    """
    name: str
    columns: list[str]
    type: str
    granularity: int = 1
    expr: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "columns": list(self.columns),
            "clickhouse_type": self.type,
            "clickhouse_granularity": self.granularity,
        }
        if self.expr is not None:
            d["expr"] = self.expr
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ChIndexSpec:
        return cls(
            name=d["name"],
            columns=list(d.get("columns", [])),
            type=d.get("clickhouse_type") or d.get("type", ""),
            granularity=d.get("clickhouse_granularity") or d.get("granularity", 1),
            expr=d.get("expr"),
        )


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


__all__ = [
    "ChIndexSpec",
    "ChTableSpec",
]
