import pytest

from dbwarden.databases.clickhouse.field import ChFieldSpec, field


class TestChFieldSpec:
    def test_defaults(self):
        spec = ChFieldSpec()
        assert spec.codec is None
        assert spec.default_expression is None
        assert spec.materialized is None
        assert spec.alias is None
        assert spec.ttl is None
        assert spec.low_cardinality is False
        assert spec.nullable is False

    def test_with_all_fields(self):
        spec = ChFieldSpec(
            codec="ZSTD(3)",
            default_expression="0",
            materialized="now()",
            alias="total",
            ttl="now() + interval 1 day",
            low_cardinality=True,
            nullable=True,
        )
        assert spec.codec == "ZSTD(3)"
        assert spec.materialized == "now()"
        assert spec.nullable is True

    def test_to_col_info_empty(self):
        assert ChFieldSpec().to_col_info() == {}

    def test_to_col_info_codec(self):
        d = ChFieldSpec(codec="ZSTD(3)").to_col_info()
        assert d == {"ch_codec": "ZSTD(3)"}

    def test_to_col_info_all(self):
        d = ChFieldSpec(
            codec="LZ4",
            default_expression="0",
            materialized="now()",
            alias="total",
            ttl="+ 1 day",
            low_cardinality=True,
            nullable=True,
        ).to_col_info()
        assert d["ch_codec"] == "LZ4"
        assert d["ch_default_expression"] == "0"
        assert d["ch_materialized"] == "now()"
        assert d["ch_alias"] == "total"
        assert d["ch_ttl"] == "+ 1 day"
        assert d["ch_low_cardinality"] is True
        assert d["ch_nullable"] is True


class TestFieldFactory:
    def test_empty(self):
        spec = field()
        assert isinstance(spec, ChFieldSpec)
        assert spec.codec is None

    def test_with_codec(self):
        spec = field(codec="ZSTD(3)")
        assert spec.codec == "ZSTD(3)"

    def test_with_nullable(self):
        spec = field(nullable=True)
        assert spec.nullable is True
