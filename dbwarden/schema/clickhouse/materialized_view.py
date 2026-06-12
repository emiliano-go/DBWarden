from __future__ import annotations

from typing import Any


def materialized_view(
    select_statement: str,
    to_table: str,
    *,
    engine: Any = None,
    order_by: str | list[str] | None = None,
    partition_by: str | None = None,
    populate: bool = False,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "ch_object_type": "materialized_view",
        "ch_select_statement": select_statement,
        "ch_to_table": to_table,
    }
    if engine is not None:
        d["ch_engine"] = engine
    if order_by is not None:
        d["ch_order_by"] = order_by
    if partition_by is not None:
        d["ch_partition_by"] = partition_by
    if populate:
        d["ch_populate"] = True
    return d
