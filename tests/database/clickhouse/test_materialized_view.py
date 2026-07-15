from dbwarden.databases.clickhouse.materialized_view import materialized_view


class TestMaterializedView:
    def test_basic(self):
        result = materialized_view(
            select_statement="SELECT id, count() FROM source GROUP BY id",
            to_table="target",
        )
        assert result["ch_object_type"] == "materialized_view"
        assert "SELECT id" in result["ch_select_statement"]
        assert result["ch_to_table"] == "target"
        assert "ch_engine" not in result
        assert "ch_populate" not in result

    def test_with_engine(self):
        result = materialized_view("SELECT 1", "t", engine="MergeTree")
        assert result["ch_engine"] == "MergeTree"

    def test_with_order_by(self):
        result = materialized_view("SELECT 1", "t", order_by="id")
        assert result["ch_order_by"] == "id"

    def test_with_partition_by(self):
        result = materialized_view("SELECT 1", "t", partition_by="toYYYYMM(date)")
        assert "toYYYYMM" in result["ch_partition_by"]

    def test_with_populate(self):
        result = materialized_view("SELECT 1", "t", populate=True)
        assert result["ch_populate"] is True

    def test_populate_defaults_false(self):
        result = materialized_view("SELECT 1", "t")
        assert "ch_populate" not in result

    def test_with_all_options(self):
        result = materialized_view(
            select_statement="SELECT id, count() FROM src GROUP BY id",
            to_table="dest",
            engine="MergeTree",
            order_by="id",
            partition_by="toYYYYMM(ts)",
            populate=True,
        )
        assert result["ch_select_statement"] == "SELECT id, count() FROM src GROUP BY id"
        assert result["ch_to_table"] == "dest"
        assert result["ch_engine"] == "MergeTree"
        assert result["ch_order_by"] == "id"
        assert result["ch_partition_by"] == "toYYYYMM(ts)"
        assert result["ch_populate"] is True
