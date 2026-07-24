from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AggExpr:
    """A typed aggregate expression for use in aggregating views.

    Carries enough information to generate BOTH sides of the aggregate-MV
    correspondence from a single declaration:
      - the target column type:      ``AggregateFunction(<func>, <types>)``
      - the MV SELECT combinator:    ``<func>State(<column>)``

    Because both derive from one ``AggExpr``, they cannot drift, which is the
    whole point of the typed door over the string door.

    Attributes:
        func: Aggregate function name (e.g. ``"sum"``, ``"avg"``, ``"count"``).
        arg: The source column / expression being aggregated (``None`` for
             ``count()``).
        arg_types: The ClickHouse type(s) of the argument, for the
            ``AggregateFunction`` signature.
        alias: Output column name in the target table.
    """
    func: str
    arg: Any
    arg_types: tuple[str, ...]
    alias: str | None = None

    def as_(self, alias: str) -> AggExpr:
        """Return a copy with the output column name set."""
        return AggExpr(self.func, self.arg, self.arg_types, alias)

    def target_type(self) -> str:
        """Render the target column type: ``AggregateFunction(func, types...)``."""
        types = ", ".join(self.arg_types)
        return f"AggregateFunction({self.func}, {types})" if types \
            else f"AggregateFunction({self.func})"

    def state_combinator(self) -> str:
        """Render the MV SELECT expression: ``funcState(arg) AS alias``."""
        inner = _render_arg(self.arg) if self.arg is not None else ""
        expr = f"{self.func}State({inner})"
        return f"{expr} AS {self.alias}" if self.alias else expr


def _render_arg(arg: Any) -> str:
    """Render an aggregate argument (a column reference or raw fragment)."""
    from dbwarden.databases.clickhouse.raw import ChRaw
    if isinstance(arg, ChRaw):
        return arg.sql
    name = getattr(arg, "name", None) or getattr(arg, "key", None)
    if name:
        return str(name)
    return str(arg)


class _AggNamespace:
    """Attribute-style aggregate constructors: ``agg.sum(col)``, ``agg.count()``.

    Attribute access (``agg.sum``) is discoverable and typo-proof, unlike
    stringly-typed function names.  ``agg.raw()`` is the passthrough for
    combinators the namespace doesn't enumerate.
    """

    def sum(  # noqa: A003
        self, arg: Any, type_: str = "Float64",
    ) -> AggExpr:
        """``SUM`` aggregate. → ``AggregateFunction(sum, type)``, ``sumState(arg)``."""
        return AggExpr("sum", arg, (type_,))

    def avg(  # noqa: A003
        self, arg: Any, type_: str = "Float64",
    ) -> AggExpr:
        """``AVG`` aggregate. → ``AggregateFunction(avg, type)``, ``avgState(arg)``."""
        return AggExpr("avg", arg, (type_,))

    def count(self) -> AggExpr:
        """``COUNT`` aggregate. → ``AggregateFunction(count)``, ``countState()``."""
        return AggExpr("count", None, ())

    def uniq_exact(self, arg: Any, type_: str) -> AggExpr:
        """``uniqExact``. → ``AggregateFunction(uniqExact, type)``."""
        return AggExpr("uniqExact", arg, (type_,))

    def uniq(self, arg: Any, type_: str) -> AggExpr:
        """``uniq``. → ``AggregateFunction(uniq, type)``."""
        return AggExpr("uniq", arg, (type_,))

    def groupArray(self, arg: Any, type_: str) -> AggExpr:  # noqa: N802
        """``groupArray``. → ``AggregateFunction(groupArray, type)``."""
        return AggExpr("groupArray", arg, (type_,))

    def groupUniqArray(self, arg: Any, type_: str) -> AggExpr:  # noqa: N802
        """``groupUniqArray``. → ``AggregateFunction(groupUniqArray, type)``."""
        return AggExpr("groupUniqArray", arg, (type_,))

    def quantile(self, arg: Any, type_: str) -> AggExpr:
        """``quantile``. → ``AggregateFunction(quantile, type)``."""
        return AggExpr("quantile", arg, (type_,))

    def any(self, arg: Any, type_: str) -> AggExpr:
        """``any``. → ``AggregateFunction(any, type)``."""
        return AggExpr("any", arg, (type_,))

    def any_last(self, arg: Any, type_: str) -> AggExpr:
        """``anyLast``. → ``AggregateFunction(anyLast, type)``."""
        return AggExpr("anyLast", arg, (type_,))

    def min(self, arg: Any, type_: str) -> AggExpr:  # noqa: A003
        return AggExpr("min", arg, (type_,))

    def max(self, arg: Any, type_: str) -> AggExpr:  # noqa: A003
        return AggExpr("max", arg, (type_,))

    def raw(  # noqa: A003
        self, func: str, arg: Any, *arg_types: str,
    ) -> AggExpr:
        """Escape hatch for combinators not enumerated above.

        Example::

            agg.raw("sumIf", amount_col, "Float64", "UInt8")
        """
        return AggExpr(func, arg, arg_types)


agg = _AggNamespace()


# ── column-type constructor ─────────────────────────────────────────────────


class ChAggStateType:
    """Declare an ``AggregateFunction`` column type.

    Renders to ``AggregateFunction(<func>, <types...>)``.

    Use in ``mapped_column()`` when declaring an ``AggregatingMergeTree`` target
    table by hand (rather than via ``aggregating_view()`` which derives the types
    automatically).

    Example::

        from dbwarden.databases.clickhouse import ch_agg_state

        amount_sum = mapped_column(ch_agg_state("sum", "Float64"))
        # → amount_sum AggregateFunction(sum, Float64)
    """

    def __init__(self, func: str, *types: str) -> None:
        self.func = func
        self.types = types

    def __repr__(self) -> str:
        types = ", ".join(self.types)
        return f"AggregateFunction({self.func}, {types})" if types \
            else f"AggregateFunction({self.func})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ChAggStateType):
            return self.func == other.func and self.types == other.types
        return NotImplemented


def ch_agg_state(func: str, *types: str) -> ChAggStateType:
    """Declare an ``AggregateFunction`` column type.

    Example::

        amount_sum = mapped_column(ch_agg_state("sum", "Float64"))
    """
    return ChAggStateType(func, *types)
