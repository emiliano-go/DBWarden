from dbwarden.databases.clickhouse.dictionary import dictionary


class TestDictionary:
    def test_basic(self):
        result = dictionary(layout="flat", source="SELECT id, name FROM source")
        assert result["ch_dict_layout"] == "flat"
        assert "id" in result["ch_dict_source"]
        assert "ch_dict_lifetime" not in result

    def test_with_lifetime(self):
        result = dictionary(layout="complex", source="SELECT 1", lifetime=300)
        assert result["ch_dict_lifetime"] == 300

    def test_with_primary_key(self):
        result = dictionary(layout="complex", source="SELECT 1", primary_key="id")
        assert result["ch_dict_primary_key"] == "id"

    def test_with_list_primary_key(self):
        result = dictionary(layout="complex", source="SELECT 1", primary_key=["id", "ts"])
        assert result["ch_dict_primary_key"] == ["id", "ts"]
