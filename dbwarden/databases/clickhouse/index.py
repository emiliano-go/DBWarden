from __future__ import annotations

from typing import Any, Literal


def skip_index(
    name: str,
    columns: list[str],
    type: Literal["minmax", "set", "bloom_filter", "ngrambf_v1", "tokenbf_v1", "hypothesis"] | str = "minmax",
    *,
    granularity: int = 1,
    expr: str | None = None,
) -> ChIndexSpec:
    """Declare a ClickHouse skip index.

    Returns a ``ChIndexSpec``; call ``.to_dict()`` at the model boundary.
    """
    from dbwarden.databases.clickhouse import ChIndexSpec
    return ChIndexSpec(name=name, columns=list(columns), type=type, granularity=granularity, expr=expr)
