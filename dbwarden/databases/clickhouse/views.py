from __future__ import annotations

from typing import Any

from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema.table_meta import CHViewMeta


class ChView:
    """Mixin base for ClickHouse view model classes.

    Optionally inherit from this mixin alongside a declarative base to
    auto-detect the backend and skip writing ``class Meta(CHViewMeta)``
    explicitly::

        from sqlalchemy.orm import declarative_base
        from dbwarden.databases.clickhouse import (
            ChView, materialized_view,
        )

        Base = declarative_base()

        class DailyMetrics(Base, ChView):
            __tablename__ = "daily_metrics"
            day = Column(Date, primary_key=True)
            total = Column(Float64)

            class Meta(CHViewMeta):
                ch = materialized_view(
                    select=func.sum(Events.amount).label("total"),
                    to_table="daily_target",
                )
    """
    class Meta(CHViewMeta):
        pass


class MaterializedView(ChView):
    """Mixin base for ClickHouse materialized view model classes.

    Use the same as :class:`ChView`.  The marker class improves readability
    and may be used by downstream tooling::

        class DailyMetrics(Base, MaterializedView):
            ...
    """


class AggregatingView(ChView):
    """Mixin base for ClickHouse aggregating view model classes.

    Use the same as :class:`ChView`.  The marker class improves readability
    and may be used by downstream tooling::

        class DailyMetrics(Base, AggregatingView):
            ...
    """


def derive_agg_target_columns(agg_result: dict) -> list[str]:
    """Extract target table column names from an :func:`aggregating_view` result.

    The target columns are: group-by keys (by name) followed by aggregate
    aliases, in the same order as produced by :func:`aggregating_view`.

    Args:
        agg_result: The dict returned by :func:`aggregating_view`.

    Returns:
        List of column names for the ``AggregatingMergeTree`` target table.
    """
    target_info = agg_result.get("ch_agg_target", {})
    return list(target_info.get("columns", []))


def _validate_view_class(model_class: type) -> None:
    """Validate that a ClickHouse view model class is properly configured.

    Checks:
      - ``class Meta`` inherits from :class:`CHViewMeta`.
      - ``Meta.ch`` is set to a :class:`MaterializedViewSpec` or a dict
        (from :func:`aggregating_view`).
      - The model has at least one primary key column.

    Called during model discovery; raises :class:`DBWardenConfigError` on
    invalid configuration.
    """
    meta = getattr(model_class, "Meta", None)
    if meta is None:
        return
    if not isinstance(meta, type) or not issubclass(meta, CHViewMeta):
        return

    ch = getattr(meta, "ch", None)
    if ch is None:
        raise DBWardenConfigError(
            f"{model_class.__name__}: CHViewMeta requires a 'ch' attribute "
            f"set to a materialized_view() or aggregating_view() spec."
        )
