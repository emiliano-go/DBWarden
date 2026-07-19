from __future__ import annotations

from typing import Any

from dbwarden.databases.clickhouse.materialized_view import (
    AggregatingViewSpec, MaterializedViewSpec,
)
from dbwarden.databases.clickhouse.data_op import DataOp, data_op
from dbwarden.databases.clickhouse.compiler import render_expr


def populate(
    spec: MaterializedViewSpec | AggregatingViewSpec | dict[str, Any],
    *,
    name: str | None = None,
    rollback: str | None = None,
) -> DataOp:
    """Create a :class:`DataOp` that populates a materialized view's target.

    Scans the spec and builds the equivalent ``INSERT INTO <target> <select>``
    SQL — exactly what a hand-written :func:`data_op` would produce, but
    derived from the spec so it stays in sync automatically.

    Args:
        spec: A view spec (or dict) from which to derive the populate SQL.
        name: Optional explicit DataOp name.  If omitted, derives from the spec.
        rollback: Optional rollback SQL (e.g. ``TRUNCATE TABLE <target>``).
            Defaults to ``None`` (irreversible — requires confirmation).

    Returns:
        A :class:`DataOp` whose ``.forward`` is ``INSERT INTO <target> <select>``.

    Raises:
        ValueError: If the spec has no usable target or select statement.
    """
    target, select_sql = _extract_populate_parts(spec)
    if not target:
        raise ValueError(
            "Cannot generate populate DataOp: spec has no target table. "
            "MaterializedView needs to=, AggregatingView needs target_name."
        )
    if not select_sql:
        raise ValueError(
            "Cannot generate populate DataOp: spec has no select statement."
        )

    data_op_name = name or f"populate_{target}"
    return data_op(
        name=data_op_name,
        forward=f"INSERT INTO {target}\n{select_sql}",
        rollback=rollback,
        requires_confirmation=rollback is None,
    )


def _extract_populate_parts(
    spec: MaterializedViewSpec | AggregatingViewSpec | dict[str, Any],
) -> tuple[str, str]:
    """Extract (target_table, select_sql) from a view spec or dict."""
    if isinstance(spec, MaterializedViewSpec):
        target = spec.to or spec.name or ""
        if spec.select is not None:
            from dbwarden.databases.clickhouse.compiler import render_expr
            select_sql = (
                ", ".join(render_expr(item) for item in spec.select)
                if isinstance(spec.select, (list, tuple))
                else render_expr(spec.select)
            )
        else:
            select_sql = ""
        return target or "", select_sql

    if isinstance(spec, AggregatingViewSpec):
        target = spec.target_name or ""
        agg_dict = spec.to_dict()
        select_sql = agg_dict.get("ch_agg_mv", {}).get("ch_select_statement", "")
        return target, select_sql

    d = spec if isinstance(spec, dict) else {}
    target = d.get("ch_to_table") or d.get("name", "")
    select_sql = d.get("ch_select_statement", "")
    return target or "", select_sql
