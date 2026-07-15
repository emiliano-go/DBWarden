from dbwarden.databases.clickhouse.index import skip_index


class TestSkipIndex:
    def test_basic(self):
        result = skip_index("ix_payload", ["payload"], "bloom_filter")
        assert result == {
            "name": "ix_payload",
            "columns": ["payload"],
            "clickhouse_type": "bloom_filter",
            "clickhouse_granularity": 1,
        }

    def test_with_granularity(self):
        result = skip_index("ix_payload", ["payload"], "bloom_filter", granularity=4)
        assert result["clickhouse_granularity"] == 4

    def test_with_expr(self):
        result = skip_index("ix_expr", ["payload"], "tokenbf_v1", expr="tokenbf_v1(payload)")
        assert result["expr"] == "tokenbf_v1(payload)"

    def test_multiple_columns(self):
        result = skip_index("ix_multi", ["a", "b", "c"], "minmax")
        assert result["columns"] == ["a", "b", "c"]

    def test_columns_copied(self):
        cols = ["a"]
        result = skip_index("ix", cols, "set")
        cols.append("b")
        assert result["columns"] == ["a"]
