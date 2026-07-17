from dbwarden.databases.clickhouse import ChTableSpec, ch_table, merge_tree, ChIndexSpec


class TestChTable:
    def test_basic(self):
        spec = ch_table(engine=merge_tree(), order_by=["id"])
        assert isinstance(spec, ChTableSpec)
        assert spec.engine.name == "MergeTree"
        assert spec.order_by == ["id"]

    def test_with_all_options(self):
        spec = ch_table(
            engine=merge_tree(),
            order_by=["user_id", "event_time"],
            primary_key="user_id",
            partition_by="toYYYYMM(event_time)",
            settings={"index_granularity": 8192},
            indexes=[ChIndexSpec("ix_a", ["a"], type="bloom_filter")],
        )
        assert spec.engine.name == "MergeTree"
        assert spec.order_by == ["user_id", "event_time"]
        assert spec.primary_key == "user_id"
        assert spec.partition_by == "toYYYYMM(event_time)"
        assert spec.settings == {"index_granularity": 8192}
        assert spec.indexes[0].name == "ix_a"

    def test_ch_table_returns_spec(self):
        spec = ch_table(engine=merge_tree())
        assert isinstance(spec, ChTableSpec)
