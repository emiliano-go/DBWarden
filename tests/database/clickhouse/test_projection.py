from dbwarden.databases.clickhouse.projection import ProjectionSpec, projection


class TestProjectionSpec:
    def test_basic(self):
        spec = ProjectionSpec(name="proj_daily", query="SELECT date, count() GROUP BY date")
        assert spec.name == "proj_daily"
        assert "GROUP BY date" in spec.query

    def test_to_dict(self):
        spec = ProjectionSpec("p", "SELECT 1")
        assert spec.to_dict() == {"name": "p", "query": "SELECT 1"}

    def test_from_dict(self):
        spec = ProjectionSpec.from_dict({"name": "p", "query": "SELECT 1"})
        assert spec.name == "p"
        assert spec.query == "SELECT 1"

    def test_from_dict_missing_query(self):
        spec = ProjectionSpec.from_dict({"name": "p"})
        assert spec.query == ""


class TestProjectionFactory:
    def test_basic(self):
        result = projection("p", "SELECT 1")
        assert result == {"name": "p", "query": "SELECT 1"}
