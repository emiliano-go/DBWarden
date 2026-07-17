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
        engine_name = engine.name if hasattr(engine, "name") else str(engine)
        _validate_mv_engine(engine_name)
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
) -> dict[str, Any]:
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
        A dict with keys ``"ch_agg_target"`` (the target table spec) and
        ``"ch_agg_mv"`` (the MV spec).  The model-discovery layer expands these
        into two tracked schema objects.

    Example::

        from dbwarden.databases.clickhouse import (
            CHTableMeta, aggregating_view, agg, merge_tree, ch_raw,
        )
        import sqlalchemy as sa

        class Events(Base):
            __tablename__ = "events"

            class Meta(CHTableMeta):
                ch_engine = merge_tree()
                ch_order_by = [Events.user_id, Events.event_time]

            user_id:    Mapped[int] = mapped_column(BigInteger)
            event_time: Mapped[datetime] = mapped_column(DateTime)
            amount:     Mapped[float] = mapped_column(Float)

        events_daily = aggregating_view(
            name="events_daily",
            source="events",
            group_by=[Events.user_id, func.toDate(Events.event_time).label("day")],
            aggregates=[
                agg.sum(Events.amount, "Float64").as_("amount_sum"),
                agg.count().as_("event_count"),
            ],
            order_by=[Events.user_id, "day"],
            partition_by=func.toYYYYMM(column("day")),
        )
    """
    from dbwarden.databases.clickhouse.compiler import (
        render_expr,
        render_expr_list,
        column_name_from_expr,
    )

    group_by = group_by or []
    aggregates = aggregates or []
    order_by = order_by or []

    if not aggregates:
        raise ValueError("aggregating_view: at least one aggregate is required")
    if not all(hasattr(a, "alias") and a.alias for a in aggregates):
        raise ValueError(
            "aggregating_view: every aggregate must have .as_(alias) set"
        )
    mv_name = f"{name}_mv"
    target = target_name or f"{name}_agg"
    source_name = _resolve_source(source)

    # Build the column list for the AggregatingMergeTree target
    target_columns = [column_name_from_expr(g) for g in group_by]
    for a in aggregates:
        target_columns.append(a.alias)

    # Build the SELECT for the MV
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

    mv_spec = materialized_view(
        name=mv_name,
        select=select_sql,
        to_table=target,
        engine=None,
        order_by=None,
    )
    return {
        "ch_agg_target": {
            "name": target,
            "columns": target_columns,
            "aggregates": aggregates,
            "order_by": render_expr_list(order_by if isinstance(order_by, list) else [order_by]),
            "partition_by": render_expr(partition_by) if partition_by is not None else None,
            "ttl": render_expr_list(ttl if isinstance(ttl, list) else [ttl]) if ttl is not None else None,
            "settings": settings,
        },
        "ch_agg_mv": mv_spec.to_dict(),
    }


def _resolve_source(source: Any) -> str:
    """Get the table name from a source reference (model class or string)."""
    if isinstance(source, str):
        return source
    tablename = getattr(source, "__tablename__", None)
    if tablename:
        return tablename
    return str(source)



