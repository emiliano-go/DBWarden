from dbwarden.schema.seed import SeedRow, DBWardenSeed, seed_data


def test_seed_row_construction():
    row = SeedRow(code="UY", name="Uruguay")
    assert row.to_dict() == {"code": "UY", "name": "Uruguay"}


def test_seed_row_empty():
    row = SeedRow()
    assert row.to_dict() == {}


def test_seed_row_multiple_values():
    row = SeedRow(a=1, b="two", c=3.0)
    d = row.to_dict()
    assert d["a"] == 1
    assert d["b"] == "two"
    assert d["c"] == 3.0


def test_dbwarden_seed_defaults():
    seed = DBWardenSeed(database="primary", version="0001", description="initial")
    assert seed.database == "primary"
    assert seed.version == "0001"
    assert seed.description == "initial"
    assert seed.on_conflict == "ignore"
    assert seed.conflict_columns is None
    assert seed.source_hash == ""


def test_dbwarden_seed_seed_id():
    seed = DBWardenSeed(database="primary", version="0001", description="test")
    assert seed.seed_id == "primary__0001"


def test_dbwarden_seed_full():
    seed = DBWardenSeed(
        database="analytics",
        version="0042",
        description="load countries",
        on_conflict="update",
        conflict_columns=["code"],
        source_hash="abc123",
    )
    assert seed.seed_id == "analytics__0042"
    assert seed.on_conflict == "update"
    assert seed.conflict_columns == ["code"]
    assert seed.source_hash == "abc123"


class TestSeedDataDecorator:

    def test_row_based_seed(self):
        @seed_data(database="primary", version="0001", description="initial countries")
        class CountrySeed:
            model = "Country"
            rows = [
                SeedRow(code="UY", name="Uruguay"),
                SeedRow(code="AR", name="Argentina"),
            ]

        meta = getattr(CountrySeed, "__dbwarden_seed__", None)
        assert meta is not None
        assert meta.database == "primary"
        assert meta.version == "0001"
        assert meta.description == "initial countries"
        assert meta.on_conflict == "ignore"
        assert meta.conflict_columns == []
        assert meta.seed_id == "primary__0001"
        assert len(CountrySeed.rows) == 2
        assert CountrySeed.rows[0].to_dict()["code"] == "UY"

    def test_logic_based_seed(self):
        @seed_data(database="primary", version="0002", description="load permissions")
        class PermissionSeed:
            model = "Permission"

            @staticmethod
            def generate(session):
                for resource in ["users", "orders"]:
                    for action in ["read", "write"]:
                        session.add(f"Permission(name='{resource}:{action}')")

        meta = getattr(PermissionSeed, "__dbwarden_seed__", None)
        assert meta is not None
        assert meta.version == "0002"

    def test_custom_on_conflict(self):
        @seed_data(database="primary", version="0003", description="with update",
                   on_conflict="update", conflict_columns=["code"])
        class UpdateSeed:
            model = "Product"
            rows = [SeedRow(code="P1", name="Product One")]

        meta = UpdateSeed.__dbwarden_seed__
        assert meta.on_conflict == "update"
        assert meta.conflict_columns == ["code"]

    def test_invalid_on_conflict(self):
        try:
            @seed_data(database="primary", version="0004", description="bad",
                       on_conflict="invalid")
            class BadSeed:
                model = "Bad"
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "on_conflict" in str(e)

    def test_source_hash_generated(self):
        @seed_data(database="primary", version="0005", description="hash test")
        class HashSeed:
            model = "Item"
            rows = [SeedRow(id=1)]

        meta = HashSeed.__dbwarden_seed__
        assert len(meta.source_hash) == 16
        assert all(c in "0123456789abcdef" for c in meta.source_hash)

    def test_reused_class_preserves_meta(self):
        @seed_data(database="primary", version="0010", description="reused")
        class ReusedSeed:
            model = "Item"

        meta = ReusedSeed.__dbwarden_seed__
        assert meta.seed_id == "primary__0010"
