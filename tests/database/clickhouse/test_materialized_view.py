from dbwarden.databases.clickhouse.materialized_view import MaterializedViewSpec, materialized_view


class TestMaterializedView:
    def test_basic(self):
        result = materialized_view(
            name="test_mv",
            select="SELECT id, count() FROM source GROUP BY id",
            to="target",
        )
        assert isinstance(result, MaterializedViewSpec)
        d = result.to_dict()
        assert d["ch_object_type"] == "materialized_view"
        assert "SELECT id" in d["ch_select_statement"]
        assert d["ch_to_table"] == "target"
        assert "ch_engine" not in d
        assert "ch_populate" not in d

    def test_with_engine(self):
        result = materialized_view(
            name="test_mv", select="SELECT 1", to="t",
            engine="MergeTree",
        )
        d = result.to_dict()
        assert d["ch_engine"] == "MergeTree"

    def test_with_order_by(self):
        result = materialized_view(
            name="test_mv", select="SELECT 1", to="t",
            order_by="id",
        )
        d = result.to_dict()
        assert d["ch_order_by"] == "id"

    def test_with_partition_by(self):
        result = materialized_view(
            name="test_mv", select="SELECT 1", to="t",
            partition_by="toYYYYMM(date)",
        )
        d = result.to_dict()
        assert "toYYYYMM" in d["ch_partition_by"]

    def test_with_populate(self):
        result = materialized_view(
            name="test_mv", select="SELECT 1", to="t",
            populate=True,
        )
        d = result.to_dict()
        assert d["ch_populate"] is True

    def test_populate_defaults_false(self):
        result = materialized_view(
            name="test_mv", select="SELECT 1", to="t",
        )
        d = result.to_dict()
        assert "ch_populate" not in d

    def test_with_all_options(self):
        result = materialized_view(
            name="test_mv",
            select="SELECT id, count() FROM src GROUP BY id",
            to="dest",
            engine="MergeTree",
            order_by="id",
            partition_by="toYYYYMM(ts)",
            populate=True,
        )
        d = result.to_dict()
        assert d["ch_select_statement"] == "SELECT id, count() FROM src GROUP BY id"
        assert d["ch_to_table"] == "dest"
        assert d["ch_engine"] == "MergeTree"
        assert d["ch_order_by"] == "id"
        assert d["ch_partition_by"] == "toYYYYMM(ts)"
        assert d["ch_populate"] is True
