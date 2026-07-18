from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any


@dataclass
class MaterializedViewSpec:
    """Typed spec for a ClickHouse materialized view.

    Expression fields (select, order_by, partition_by, ttl) accept
    :class:`~sqlalchemy.sql.ColumnElement`, :class:`ChRaw`, or plain ``str``.
    When a ``ColumnElement`` is provided, it is rendered to ClickHouse SQL via
    :func:`render_expr`.

    Attributes:
        name: View name.
        select: The SELECT query.
        to_table: Explicit target table, or None for implicit ``.inner.`` storage.
        refresh: Refresh schedule (e.g. ``"EVERY 1 HOUR"``).
        populate: If True, emit ``POPULATE`` for one-time backfill.
        engine: Engine spec for implicit-storage MVs.
        order_by: ORDER BY for implicit-storage MVs.
        partition_by: Optional PARTITION BY.
        ttl: Optional TTL expression(s).
        settings: Optional engine SETTINGS.
    """
    name: str | None = None
    select: Any = None
    to_table: str | None = None
    refresh: str | None = None
    populate: bool = False
    engine: Any = None
    order_by: Any = None
    partition_by: Any = None
    ttl: Any = None
    settings: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        from dbwarden.databases.clickhouse.compiler import render_expr, render_expr_list

        d: dict[str, Any] = {
            "ch_object_type": "materialized_view",
            "ch_select_statement": render_expr(self.select) if self.select is not None else None,
        }
        if self.to_table is not None:
            d["ch_to_table"] = self.to_table
        if self.refresh is not None:
            d["ch_refresh"] = self.refresh
        if self.populate:
            d["ch_populate"] = True
        if self.engine is not None:
            from dbwarden.databases.clickhouse.engine import ChEngineSpec
            if isinstance(self.engine, ChEngineSpec):
                d["ch_engine_raw"] = self.engine.to_dict()
                d["ch_engine"] = self.engine.name
            else:
                d["ch_engine"] = self.engine
        if self.order_by is not None:
            d["ch_order_by"] = (
                render_expr_list(self.order_by)
                if isinstance(self.order_by, list)
                else render_expr(self.order_by)
            )
        if self.partition_by is not None:
            d["ch_partition_by"] = render_expr(self.partition_by)
        if self.ttl is not None:
            d["ch_ttl"] = (
                render_expr_list(self.ttl)
                if isinstance(self.ttl, list)
                else [render_expr(self.ttl)]
            )
        if self.settings is not None:
            d["ch_settings"] = dict(self.settings)
        return d


def _select_items_have_aggregates(items: list) -> bool:
    """Check if a structured select list contains aggregate functions."""
    from sqlalchemy.sql.elements import Label
    from sqlalchemy.sql.functions import FunctionElement

    _AGGREGATE_NAMES = frozenset({
        "sum", "count", "avg", "min", "max", "any", "uniq",
        "groupArray", "groupUniqArray",
    })

    for item in items:
        inner = item
        # Unwrap Label to get the underlying expression
        if isinstance(inner, Label):
            inner = inner.element
        if isinstance(inner, FunctionElement):
            name = getattr(inner, "name", None) or getattr(inner, "__class__", None)
            func_name = str(name).lower().split(".")[-1] if name else ""
            if func_name in _AGGREGATE_NAMES:
                return True
            if func_name.endswith("state") or func_name.endswith("merge"):
                return True
    return False


def materialized_view(
    *,
    name: str | None = None,
    select: Any = None,
    to_table: str | None = None,
    refresh: str | None = None,
    populate: bool = False,
    engine: Any = None,
    order_by: Any = None,
    partition_by: Any = None,
    ttl: Any = None,
    settings: dict[str, str] | None = None,
) -> MaterializedViewSpec:
    """Declare a ClickHouse materialized view.

    Two storage shapes, which diff differently:
      - ``to_table`` set:   MV writes into an explicit target table
        (modern, preferred).
      - ``to_table`` None:  MV owns implicit ``.inner.`` storage;
        ``engine`` and ``order_by`` are required.

    Returns a ``MaterializedViewSpec``; call ``.to_dict()`` at the model boundary.

    Expression fields (select, order_by, partition_by, ttl) accept
    :class:`~sqlalchemy.sql.ColumnElement`, :class:`ChRaw`, or plain ``str``.
    When a ``ColumnElement`` is provided, it is rendered to ClickHouse SQL via
    :func:`render_expr`.

    Args:
        name: View name.
        select: The SELECT.  A :class:`~sqlalchemy.sql.ColumnElement`,
            ``ch_raw()``, or plain string.
        to_table: Explicit target table name, or None for implicit storage.
        refresh: Refresh schedule for refreshable MVs, e.g. ``"EVERY 1 HOUR"``.
            This IS converged schema state — changing it emits an ALTER.
        populate: If True, emit ``POPULATE`` for a one-time backfill.  This is a
            DATA-LIFECYCLE op, NOT converged: it routes to the one-time path and
            is applied once, never re-emitted on subsequent diffs.
        engine: Engine spec for implicit-storage MVs (required when to_table is
            None).
        order_by: ORDER BY for implicit-storage MVs.
        partition_by: Optional PARTITION BY.
        ttl: Optional TTL expression(s).
        settings: Optional engine SETTINGS.

    Raises:
        ValueError: if ``to_table`` is None and ``engine`` is not provided.
        ValueError: if ``populate`` and ``refresh`` are both set (incompatible).
    """
    if to_table is None and engine is None:
        raise ValueError(
            "materialized_view: engine is required when to_table is None "
            "(implicit .inner. storage)"
        )
    if to_table is None and engine is not None:
        from dbwarden.databases.clickhouse.views import _validate_mv_engine
        from dbwarden.databases.clickhouse.raw import ChRaw
        engine_name = engine.name if hasattr(engine, "name") else str(engine)
        select_is_raw = isinstance(select, (str, ChRaw))
        has_aggregates = False
        if not select_is_raw and isinstance(select, (list, tuple)):
            has_aggregates = _select_items_have_aggregates(select)
        _validate_mv_engine(
            engine_name,
            has_aggregates=has_aggregates,
            select_is_raw=select_is_raw,
        )
    if populate and refresh:
        raise ValueError(
            "materialized_view: populate and refresh are mutually exclusive"
        )

    return MaterializedViewSpec(
        name=name,
        select=select,
        to_table=to_table,
        refresh=refresh,
        populate=populate,
        engine=engine,
        order_by=order_by,
        partition_by=partition_by,
        ttl=ttl,
        settings=settings,
    )


@dataclass
class AggregatingViewSpec:
    """Typed spec for a ClickHouse aggregating view (source -> target -> MV triad).

    Returned by :func:`aggregating_view`.  Call ``.to_dict()`` at the model
    serialization boundary to produce the dict format consumed by the
    discovery and expansion pipeline.

    Expression fields (group_by, order_by, partition_by, ttl) accept
    :class:`~sqlalchemy.sql.ColumnElement`, :class:`ChRaw`, or plain ``str``.
    """
    name: str
    source: Any
    group_by: Any = None
    aggregates: Any = None
    order_by: Any = None
    partition_by: Any = None
    ttl: Any = None
    settings: dict[str, str] | None = None
    target_name: str | None = None

    @property
    def mv_name(self) -> str:
        return f"{self.name}_mv"

    @property
    def target_table_name(self) -> str:
        return self.target_name or f"{self.name}_agg"

    @property
    def target_columns(self) -> list[str]:
        from dbwarden.databases.clickhouse.compiler import column_name_from_expr
        cols: list[str] = []
        for g in (self.group_by or []):
            cols.append(column_name_from_expr(g))
        for a in (self.aggregates or []):
            cols.append(a.alias)
        return cols

    def to_dict(self) -> dict[str, Any]:
        from dbwarden.databases.clickhouse.compiler import (
            render_expr,
            render_expr_list,
            column_name_from_expr,
        )

        group_by = self.group_by or []
        aggregates = self.aggregates or []
        order_by = self.order_by or []
        target = self.target_table_name
        mv_name = self.mv_name
        source_name = _resolve_source(self.source)

        group_parts = [render_expr(g) for g in group_by]
        select_items = list(group_parts) + [
            a.state_combinator() for a in aggregates
        ]

        select_sql = (
            "SELECT\n    " + ",\n    ".join(select_items) +
            "\nFROM " + source_name +
            "\nGROUP BY " + ", ".join(
                column_name_from_expr(g) for g in group_by
            )
        )

        target_columns = list(self.target_columns)

        target_opts: dict[str, Any] = {
            "name": target,
            "columns": target_columns,
            "aggregates": aggregates,
            "order_by": render_expr_list(order_by if isinstance(order_by, list) else [order_by]),
        }
        if self.partition_by is not None:
            target_opts["partition_by"] = render_expr(self.partition_by)
        if self.ttl is not None:
            target_opts["ttl"] = (
                render_expr_list(self.ttl)
                if isinstance(self.ttl, list)
                else [render_expr(self.ttl)]
            )
        if self.settings is not None:
            target_opts["settings"] = dict(self.settings)

        mv_spec = MaterializedViewSpec(
            name=mv_name,
            select=select_sql,
            to_table=target,
        )

        return {
            "ch_agg_target": target_opts,
            "ch_agg_mv": mv_spec.to_dict(),
        }


def aggregating_view(
    *,
    name: str,
    source: Any,
    group_by: Any = None,
    aggregates: Any = None,
    order_by: Any = None,
    partition_by: Any = None,
    ttl: Any = None,
    settings: dict[str, str] | None = None,
    target_name: str | None = None,
) -> AggregatingViewSpec:
    """Declare an aggregate rollup as a coherent source->target->MV triad.

    Generates THREE DDL objects from one declaration:
      1. An ``AggregatingMergeTree`` target table whose columns are the
         ``AggregateFunction(...)`` types derived from ``aggregates``.
      2. A materialized view whose SELECT uses the matching
         ``<func>State(...)`` combinators, ``TO`` the target.
      3. The source table (referenced, not created — it must already exist).

    Because both the target column types and the MV combinators derive from the
    same list of ``AggExpr``, they are guaranteed consistent — the correspondence
    that is manual and drift-prone in the string-SELECT form is here derived and
    safe.

    Expression fields (group_by, order_by, partition_by, ttl) accept
    :class:`~sqlalchemy.sql.ColumnElement`, :class:`ChRaw`, or plain ``str``.
    When a ``ColumnElement`` is provided, it is rendered to ClickHouse SQL via
    :func:`render_expr`.

    Args:
        name: Logical name; the MV is ``<name>_mv`` and the target defaults to
            ``<name>_agg`` unless ``target_name`` is given.
        source: The source table name (a model class or string).  The MV's
            ``FROM`` clause references this.
        group_by: ``GROUP BY`` keys — :class:`~sqlalchemy.sql.ColumnElement`,
            ``ch_raw()``, or strings.
        aggregates: The aggregate columns, as ``AggExpr`` (from ``agg.*``), each
            with ``.as_(alias)`` set.
        order_by: ``ORDER BY`` for the ``AggregatingMergeTree`` target.
        partition_by: Optional ``PARTITION BY`` for the target.
        ttl: Optional TTL for the target.
        settings: Optional engine ``SETTINGS`` for the target.
        target_name: Override the target table name (defaults to
            ``<name>_agg``).

    Returns:
        An :class:`AggregatingViewSpec`; call ``.to_dict()`` at the model boundary.

    Example::

        from dbwarden.databases.clickhouse import (
            AggregatingViewSpec, aggregating_view, agg,
        )
        import sqlalchemy as sa
        from sqlalchemy import column, func

        events_daily = aggregating_view(
            name="events_daily",
            source="events",
            group_by=[column("user_id"), func.toDate(column("event_time")).label("day")],
            aggregates=[
                agg.sum(column("amount"), "Float64").as_("amount_sum"),
                agg.count().as_("event_count"),
            ],
            order_by=[column("user_id"), "day"],
            partition_by=func.toYYYYMM(column("day")),
        )
    """
    from dbwarden.databases.clickhouse.compiler import column_name_from_expr

    group_by = group_by or []
    aggregates = aggregates or []

    if not aggregates:
        raise ValueError("aggregating_view: at least one aggregate is required")
    if not all(hasattr(a, "alias") and a.alias for a in aggregates):
        raise ValueError(
            "aggregating_view: every aggregate must have .as_(alias) set"
        )

    return AggregatingViewSpec(
        name=name,
        source=source,
        group_by=group_by,
        aggregates=aggregates,
        order_by=order_by,
        partition_by=partition_by,
        ttl=ttl,
        settings=settings,
        target_name=target_name,
    )


def _resolve_source(source: Any) -> str:
    """Get the table name from a source reference (model class or string)."""
    if isinstance(source, str):
        return source
    tablename = getattr(source, "__tablename__", None)
    if tablename:
        return tablename
    return str(source)



