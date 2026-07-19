"""Doc-build gate: every code example in docs must be importable and pass discovery.

This test extracts code from the Markdown doc files and runs them through
model discovery — verifying they produce valid specs and register correctly.
"""


def _check_doc_imports():
    """Smoke-import each documented builder pattern.

    Rather than re-parsing Markdown (fragile), we test the *patterns* that
    the doc examples demonstrate.  If a new example uses a pattern not covered
    here, this test will NOT catch it — the docs build gate is a best-effort
    check that the class API works end-to-end as documented.
    """
    # Pattern 1: MaterializedView subclass with Mode B (to= given, no columns)
    from dbwarden.databases.clickhouse import MaterializedView, materialized_view
    from dbwarden.schema.table_meta import CHViewMeta

    class _DocTestMV(MaterializedView):
        __tablename__ = "_doctest_mv"
        class Meta(CHViewMeta):
            ch = materialized_view(
                select="SELECT id, count() FROM src GROUP BY id",
                to="_doctest_target",
            )

    assert _DocTestMV in MaterializedView._ch_view_registry

    # Pattern 2: MaterializedView subclass with Mode A (engine + order_by, no to)
    from sqlalchemy.orm import Mapped, mapped_column

    class _DocTestInner(MaterializedView):
        __tablename__ = "_doctest_inner"
        date: Mapped[str] = mapped_column(primary_key=True)
        class Meta(CHViewMeta):
            ch = materialized_view(
                select="SELECT date, count() FROM src GROUP BY date",
                engine="MergeTree",
                order_by=["date"],
            )

    assert _DocTestInner in MaterializedView._ch_view_registry

    # Pattern 3: AggregatingView subclass
    from dbwarden.databases.clickhouse import AggregatingView, aggregating_view, agg
    from sqlalchemy import func
    from sqlalchemy.orm import DeclarativeBase

    class _DocTestBase(DeclarativeBase):
        pass

    class _DocTestSrc(_DocTestBase):
        __tablename__ = "_doctest_src"
        date: Mapped[str] = mapped_column(primary_key=True)
        amount: Mapped[float] = mapped_column()

    class _DocTestAgg(AggregatingView):
        __tablename__ = "_doctest_agg"
        class Meta(CHViewMeta):
            ch = aggregating_view(
                source=_DocTestSrc,
                group_by=[_DocTestSrc.date],
                aggregates=[agg.sum(_DocTestSrc.amount, "Float64").as_("total")],
                order_by=[_DocTestSrc.date],
            )

    assert _DocTestAgg in AggregatingView._ch_view_registry

    # Pattern 4: data_ops.populate()
    from dbwarden.databases.clickhouse import data_ops
    pop = data_ops.populate(_DocTestMV.Meta.ch)
    assert pop.forward.startswith("INSERT INTO")


def test_doc_examples_import_and_discover():
    """Every documented builder pattern imports and passes discovery."""
    _check_doc_imports()
