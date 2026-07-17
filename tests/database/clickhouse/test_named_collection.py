from __future__ import annotations

from dbwarden.databases.clickhouse.named_collection import NamedCollectionSpec, named_collection
from dbwarden.engine.backends.clickhouse.secrets import _REDACTED, strip_secret_values


class TestNamedCollectionSpec:
    def test_basic(self):
        nc = named_collection("kafka_prod", kafka_broker_list="broker:9092")
        assert nc.name == "kafka_prod"
        assert nc.entries == {"kafka_broker_list": "broker:9092"}

    def test_to_dict(self):
        nc = named_collection("s3_creds", access_key_id="AKID", secret_access_key="sk-123")
        d = nc.to_dict()
        assert d["name"] == "s3_creds"
        assert d["entries"]["access_key_id"] == "AKID"

    def test_overridable(self):
        nc = named_collection("cfg", overridable={"k1": False}, k1="v1")
        assert nc.overridable == {"k1": False}
        d = nc.to_dict()
        assert d["overridable"] == {"k1": False}

    def test_strip_secret_values(self):
        spec = {"k1": "v1", "k2": "secret"}
        result = strip_secret_values(spec, frozenset({"k2"}))
        assert result["k1"] == "v1"
        assert result["k2"] == _REDACTED

    def test_strip_unconditional(self):
        spec = {"k1": "visible"}
        result = strip_secret_values(spec, frozenset({"k1"}))
        assert result["k1"] == _REDACTED
