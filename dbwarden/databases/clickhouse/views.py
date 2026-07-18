from __future__ import annotations

import warnings
from typing import Any

from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema.table_meta import CHViewMeta
from dbwarden.engine.core.models import ModelColumn, ModelTable
from dbwarden.databases.clickhouse import AggregatingViewSpec, MaterializedViewSpec


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


def derive_agg_target_columns(agg_result: AggregatingViewSpec | dict) -> list[str]:
    """Extract target table column names from an :func:`aggregating_view` result.

    The target columns are: group-by keys (by name) followed by aggregate
    aliases, in the same order as produced by :func:`aggregating_view`.

    Args:
        agg_result: The :class:`AggregatingViewSpec` or dict returned by
            :func:`aggregating_view`.

    Returns:
        List of column names for the ``AggregatingMergeTree`` target table.
    """
    if isinstance(agg_result, AggregatingViewSpec):
        return list(agg_result.target_columns)
    target_info = agg_result.get("ch_agg_target", {})
    return list(target_info.get("columns", []))


_COLLAPSING_ENGINES = frozenset({
    "SummingMergeTree", "ReplicatedSummingMergeTree",
    "AggregatingMergeTree", "ReplicatedAggregatingMergeTree",
    "ReplacingMergeTree", "ReplicatedReplacingMergeTree",
    "CollapsingMergeTree", "ReplicatedCollapsingMergeTree",
    "VersionedCollapsingMergeTree", "ReplicatedVersionedCollapsingMergeTree",
    "GraphiteMergeTree", "ReplicatedGraphiteMergeTree",
})

_MERGETREE_FAMILY = frozenset({
    "MergeTree", "ReplicatedMergeTree",
    "SummingMergeTree", "ReplicatedSummingMergeTree",
    "AggregatingMergeTree", "ReplicatedAggregatingMergeTree",
    "ReplacingMergeTree", "ReplicatedReplacingMergeTree",
    "CollapsingMergeTree", "ReplicatedCollapsingMergeTree",
    "VersionedCollapsingMergeTree", "ReplicatedVersionedCollapsingMergeTree",
    "GraphiteMergeTree", "ReplicatedGraphiteMergeTree",
})


def _validate_mv_engine(
    engine_name: str,
    *,
    has_aggregates: bool = False,
    select_is_raw: bool = False,
) -> None:
    """Validate engine choice for a materialized view.

    An MV's SELECT runs per INSERTED BLOCK, not over the full table.  A
    non-collapsing engine therefore ACCUMULATES one partial-aggregate row per
    insert forever, and reads return an arbitrary partial.  This is silent: no
    error, wrong numbers.

    Two verification paths, because a raw-SQL select is opaque:

    *Structured select* (``select_is_raw=False``, ``has_aggregates`` set by the
    caller after inspecting the ``ColumnElement`` list).  When the select
    aggregates and the engine can't collapse rows, this raises ``ValueError``.

    *Raw select* (``select_is_raw=True``).  The validator cannot inspect the
    SQL, so it emits an advisory ``UserWarning`` instead of a hard error.  The
    user owns collapse-correctness.

    Raises:
        ValueError: if engine is not MergeTree-family (implicit-storage MVs).
        ValueError: if ``has_aggregates`` is True and engine is not in
            ``_COLLAPSING_ENGINES``.
        UserWarning: if ``select_is_raw`` and engine is not collapsing.
    """
    if engine_name not in _MERGETREE_FAMILY:
        raise ValueError(
            f"Invalid engine for materialized view: "
            f"{engine_name!r}. Must be one of MergeTree family."
        )

    if has_aggregates and engine_name not in _COLLAPSING_ENGINES:
        raise ValueError(
            f"Engine {engine_name!r} cannot collapse partial-aggregate rows. "
            f"Aggregating SELECTs on a non-collapsing engine accumulate one "
            f"partial row per insert block forever; reads silently return an "
            f"arbitrary partial. "
            f"Use aggregating_view() for AggregateFunction columns with -State "
            f"combinators, or an explicit collapsing engine "
            f"(summing_merge_tree(), aggregating_merge_tree(), etc.) if "
            f"partial-sum merging on ORDER BY is what is wanted."
        )

    if select_is_raw and engine_name not in _COLLAPSING_ENGINES:
        warnings.warn(
            f"Engine {engine_name!r} is not in the collapsing family "
            f"(SummingMergeTree, AggregatingMergeTree, etc.) and the SELECT "
            f"was provided as raw SQL — the validator cannot verify "
            f"collapse-safety. If the SELECT uses aggregate functions, this "
            f"will silently accumulate partial rows per insert. "
            f"Prefer structured select items (ColumnElement list) or a "
            f"collapsing engine.",
            UserWarning,
            stacklevel=2,
        )


def get_all_ch_views(
    model_paths: list[str] | None = None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    """Scan all model classes and return ClickHouse view specs.

    Returns a list of dicts, each with:
      - ``model_class``: the SQLAlchemy model class
      - ``spec``: the view spec (``MaterializedViewSpec``, or a dict from
        :func:`aggregating_view`)
      - ``view_type``: ``"materialized_view"`` or ``"aggregating_view"``

    Views from the module-level API (loose ``ch_*`` attrs) are NOT included;
    only class-based API views using ``CHViewMeta`` + ``materialized_view()``
    or ``aggregating_view()`` are returned.

    Args:
        model_paths: Paths to model files or directories.
        db_name: Database name override.

    Returns:
        List of view spec dicts.
    """
    from dbwarden.engine.model_discovery.path_discovery import (
        auto_discover_model_paths,
        _collect_model_files,
        load_model_from_path,
    )

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    model_files = _collect_model_files(model_paths)
    results: list[dict[str, Any]] = []

    for model_file in model_files:
        module = load_model_from_path(model_file)
        if module is None:
            continue
        for attr in module.__dict__.values():
            if not isinstance(attr, type):
                continue
            if getattr(attr, "__module__", None) != getattr(module, "__name__", None):
                continue
            tablename = getattr(attr, "__tablename__", None)
            table_obj = getattr(attr, "__table__", None)
            if tablename is None or table_obj is None:
                continue
            meta = attr.__dict__.get("Meta") if hasattr(attr, "Meta") else None
            if meta is None or not isinstance(meta, type):
                continue
            if not issubclass(meta, CHViewMeta):
                continue
            ch_spec = getattr(meta, "ch", None)
            if ch_spec is None:
                continue
            if isinstance(ch_spec, MaterializedViewSpec):
                results.append({
                    "model_class": attr,
                    "spec": ch_spec,
                    "view_type": "materialized_view",
                })
            elif isinstance(ch_spec, AggregatingViewSpec):
                results.append({
                    "model_class": attr,
                    "spec": ch_spec,
                    "view_type": "aggregating_view",
                })

    return results


def ch_view_tables_from_models(
    model_paths: list[str] | None = None,
    db_name: str | None = None,
) -> list[ModelTable]:
    """Extract ModelTables from CH view model classes, expanding aggregating
    views into their constituent MV + target table.

    Returns a list of ``ModelTable`` instances that can be appended to the
    output of ``get_all_model_tables()``.
    """
    from dbwarden.engine.model_discovery.extraction import extract_table_from_model

    views = get_all_ch_views(model_paths=model_paths, db_name=db_name)
    tables: list[ModelTable] = []

    for entry in views:
        model_class = entry["model_class"]
        view_type = entry["view_type"]

        # Extract the MV's ModelTable
        mv_table = extract_table_from_model(model_class, db_name=db_name)
        if mv_table:
            tables.append(mv_table)

        # For aggregating views, also create the target table ModelTable
        if view_type == "aggregating_view":
            target_table = _expand_agg_target(model_class, entry["spec"])
            if target_table:
                tables.append(target_table)

    return tables


def _expand_agg_target(
    model_class: type,
    agg_spec: AggregatingViewSpec | dict[str, Any],
) -> ModelTable | None:
    """Create a synthetic ModelTable for the aggregating view target table.

    The target is an ``AggregatingMergeTree`` table whose columns are derived
    from the model class columns (group-by keys + aggregate columns).
    """
    if isinstance(agg_spec, AggregatingViewSpec):
        agg_dict = agg_spec.to_dict()
        target_info = agg_dict["ch_agg_target"]
    else:
        target_info = agg_spec.get("ch_agg_target", {})
    target_name = target_info.get("name")
    if not target_name:
        return None

    order_by = target_info.get("order_by")
    partition_by = target_info.get("partition_by")
    ttl = target_info.get("ttl")
    settings = target_info.get("settings")

    clickhouse_options: dict[str, Any] = {
        "ch_engine": "AggregatingMergeTree",
        "ch_object_type": "table",
    }
    if order_by is not None:
        clickhouse_options["ch_order_by"] = (
            [order_by] if isinstance(order_by, str) else list(order_by)
        )
    if partition_by is not None:
        clickhouse_options["ch_partition_by"] = partition_by
    if ttl is not None:
        clickhouse_options["ch_ttl"] = [ttl] if isinstance(ttl, str) else list(ttl)
    if settings is not None:
        clickhouse_options["ch_settings"] = dict(settings)

    columns = _make_target_columns(model_class, target_info)
    return ModelTable(
        name=target_name,
        columns=columns,
        clickhouse_options=clickhouse_options,
        object_type="table",
    )


def _make_target_columns(
    model_class: type,
    target_info: dict[str, Any],
) -> list[ModelColumn]:
    """Build ModelColumn list for the aggregating view target table.

    Copies column definitions from the model class, which has the same columns
    as the target (the target uses ``AggregateFunction`` types where the MV
    uses ``-State`` combinators).
    """
    column_names = target_info.get("columns", [])
    col_name_set = set(column_names)
    columns: list[ModelColumn] = []

    table = getattr(model_class, "__table__", None)
    if table is not None:
        for sa_col in table.columns:
            if sa_col.name not in col_name_set:
                continue
            columns.append(ModelColumn(
                name=sa_col.name,
                type=str(sa_col.type),
                nullable=sa_col.nullable,
                primary_key=sa_col.primary_key,
                unique=sa_col.unique,
                default=str(sa_col.default) if sa_col.default is not None else None,
                foreign_key=None,
                comment=sa_col.comment or None,
            ))

    for name in column_names:
        if name not in {c.name for c in columns}:
            columns.append(ModelColumn(
                name=name,
                type="String",
                nullable=True,
                primary_key=False,
                unique=False,
                default=None,
                foreign_key=None,
            ))

    return columns


def _has_user_columns(cls: type) -> bool:
    """Check if a class declares user-level mapped columns or column-like attrs.

    Inspects ``cls.__dict__`` for ``Column``/``MappedColumn`` instances and
    ``cls.__annotations__`` for ``Mapped[...]`` type hints.  ``__tablename__``,
    ``__abstract__``, ``Meta``, and dunder attrs are excluded.

    Works on both SQLAlchemy-DeclarativeBase subclasses (which have
    ``__table__``) and plain ``ChView`` subclasses (which don't — see Phase B),
    because it checks ``__dict__`` rather than ``__table__.c``.
    """
    from sqlalchemy import Column as SAColumn
    from sqlalchemy.orm import MappedColumn
    from sqlalchemy.orm import Mapped as MappedDescriptor

    # Check for Column or MappedColumn instances assigned in the class body
    for val in cls.__dict__.values():
        if isinstance(val, (SAColumn, MappedColumn)):
            return True

    # Check for Mapped[...] annotations
    for attr_name, attr_type in cls.__annotations__.items():
        if attr_name.startswith("_"):
            continue
        if attr_name in ("__tablename__", "__abstract__"):
            continue
        origin = getattr(attr_type, "__origin__", None)
        if origin is MappedDescriptor:
            return True

    return False


def _validate_view_class(model_class: type) -> None:
    """Validate that a ClickHouse view model class is properly configured.

    Checks:
      - ``class Meta`` inherits from :class:`CHViewMeta`.
      - ``Meta.ch`` is set to a :class:`MaterializedViewSpec` or
        :class:`AggregatingViewSpec`.
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
    if not isinstance(ch, (MaterializedViewSpec, AggregatingViewSpec)):
        raise DBWardenConfigError(
            f"{model_class.__name__}: 'ch' attribute must be a "
            f"MaterializedViewSpec or AggregatingViewSpec, got {type(ch).__name__}."
        )

    tablename = getattr(model_class, "__tablename__", None)
    if tablename is None:
        raise DBWardenConfigError(
            f"{model_class.__name__}: CHViewMeta model must have __tablename__ set."
        )

    if isinstance(ch, MaterializedViewSpec):
        if ch.to is not None:
            # Mode B — the class is the MV; no columns, no engine, no order_by
            if ch.engine is not None:
                raise TypeError(
                    f"{model_class.__name__}: MaterializedView in Mode B "
                    f"(to= given) must not declare engine — the engine belongs "
                    f"to the target table, which this class does not own."
                )
            if ch.order_by is not None:
                raise TypeError(
                    f"{model_class.__name__}: MaterializedView in Mode B "
                    f"(to= given) must not declare order_by — it belongs to "
                    f"the target table."
                )
            if _has_user_columns(model_class):
                raise TypeError(
                    f"{model_class.__name__}: MaterializedView in Mode B "
                    f"(to= given) must not declare columns — columns belong "
                    f"to the target table."
                )
        if ch.name is not None and ch.name != tablename:
            warnings.warn(
                f"materialized_view(name=...) is deprecated when used inside a class body. "
                f"The view name is derived from __tablename__ ('{tablename}'). "
                f"Passed name '{ch.name}' will be ignored.",
                DeprecationWarning,
                stacklevel=2,
            )
        ch.name = tablename
    elif isinstance(ch, AggregatingViewSpec):
        if _has_user_columns(model_class):
            raise TypeError(
                f"{model_class.__name__}: AggregatingView columns are "
                f"derived from group_by + aggregates, not declared. "
                f"Remove column declarations."
            )
        if ch.name != tablename:
            warnings.warn(
                f"aggregating_view(name=...) is deprecated when used inside a class body. "
                f"The view name is derived from __tablename__ ('{tablename}'). "
                f"Passed name '{ch.name}' will be ignored.",
                DeprecationWarning,
                stacklevel=2,
            )
        ch.name = tablename
