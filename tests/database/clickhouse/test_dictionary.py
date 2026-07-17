from dbwarden.databases.clickhouse.dictionary import DictSpec, dictionary


class TestDictionary:
    def test_basic(self):
        result = dictionary(layout="flat", source="SELECT id, name FROM source")
        assert isinstance(result, DictSpec)
        assert result.layout == "flat"
        assert "id" in result.source
        assert result.lifetime is None

    def test_with_lifetime(self):
        result = dictionary(layout="complex", source="SELECT 1", lifetime=300)
        assert result.lifetime == 300

    def test_with_primary_key(self):
        result = dictionary(layout="complex", source="SELECT 1", primary_key="id")
        assert result.primary_key == "id"

    def test_with_list_primary_key(self):
        result = dictionary(layout="complex", source="SELECT 1", primary_key=["id", "ts"])
        assert result.primary_key == ["id", "ts"]

    def test_to_dict(self):
        result = dictionary(layout="flat", source="SELECT 1", lifetime=300)
        d = result.to_dict()
        assert d["ch_dict_layout"] == "flat"
        assert d["ch_dict_lifetime"] == 300
