import pytest

from dbwarden.databases.clickhouse.engine import (
    ChEngineSpec,
    _split_engine_args,
    merge_tree,
    replacing_merge_tree,
    replicated_merge_tree,
    summing_merge_tree,
    aggregating_merge_tree,
)


class TestSplitEngineArgs:
    def test_empty_string(self):
        assert _split_engine_args("") == []

    def test_single_arg(self):
        assert _split_engine_args("foo") == ["foo"]

    def test_multiple_args(self):
        assert _split_engine_args("a, b, c") == ["a", "b", "c"]

    def test_args_with_parens(self):
        assert _split_engine_args("(a, b), c") == ["(a, b)", "c"]

    def test_args_with_quotes(self):
        assert _split_engine_args("'/zk/path', 'replica'") == ["'/zk/path'", "'replica'"]


class TestChEngineSpec:
    def test_basic_engine(self):
        spec = ChEngineSpec("MergeTree")
        assert spec.name == "MergeTree"
        assert spec.args == ()
        assert spec.zookeeper_path is None

    def test_with_args(self):
        spec = ChEngineSpec("SummingMergeTree", args=("col1", "col2"))
        assert spec.args == ("col1", "col2")

    def test_args_normalized_in_post_init(self):
        spec = ChEngineSpec("SummingMergeTree", args=["col1", "col2"])
        assert spec.args == ("col1", "col2")

    def test_args_string_in_post_init(self):
        spec = ChEngineSpec("Test", args="single")
        assert spec.args == ("single",)

    def test_to_dict_basic(self):
        spec = ChEngineSpec("MergeTree")
        assert spec.to_dict() == {"name": "MergeTree"}

    def test_to_dict_with_args(self):
        spec = ChEngineSpec("SummingMergeTree", args=("col1",))
        assert spec.to_dict() == {"name": "SummingMergeTree", "args": ("col1",)}

    def test_to_dict_with_zookeeper(self):
        spec = ChEngineSpec("ReplicatedMergeTree", zookeeper_path="/zk/path", replica_name="r1")
        d = spec.to_dict()
        assert d["zookeeper_path"] == "/zk/path"
        assert d["replica_name"] == "r1"

    def test_to_dict_with_settings(self):
        spec = ChEngineSpec("MergeTree", settings={"max_bytes": "1GB"})
        assert spec.to_dict()["settings"] == {"max_bytes": "1GB"}

    def test_from_dict(self):
        d = {"name": "MergeTree", "args": ("col1",), "settings": {"a": "b"}}
        spec = ChEngineSpec.from_dict(d)
        assert spec.name == "MergeTree"
        assert spec.args == ("col1",)
        assert spec.settings == {"a": "b"}

    def test_from_dict_empty_settings(self):
        spec = ChEngineSpec.from_dict({"name": "MergeTree", "settings": {}})
        assert spec.settings is None

    def test_from_engine_string_basic(self):
        spec = ChEngineSpec.from_engine_string("MergeTree()")
        assert spec.name == "MergeTree"

    def test_from_engine_string_with_args(self):
        spec = ChEngineSpec.from_engine_string("SummingMergeTree(col1, col2)")
        assert spec.name == "SummingMergeTree"
        assert spec.args == ("col1", "col2")

    def test_from_engine_string_replicated(self):
        spec = ChEngineSpec.from_engine_string("ReplicatedMergeTree('/zk/path', 'r1', ver)")
        assert spec.name == "ReplicatedMergeTree"
        assert spec.zookeeper_path == "/zk/path"
        assert spec.replica_name == "r1"
        assert spec.args == ("ver",)


class TestEngineFactories:
    def test_merge_tree(self):
        spec = merge_tree()
        assert spec.name == "MergeTree"

    def test_merge_tree_with_settings(self):
        spec = merge_tree(settings={"a": "b"})
        assert spec.settings == {"a": "b"}

    def test_replacing_merge_tree(self):
        spec = replacing_merge_tree()
        assert spec.name == "ReplacingMergeTree"
        assert spec.args == ()

    def test_replacing_merge_tree_with_version(self):
        spec = replacing_merge_tree("ver")
        assert spec.args == ("ver",)

    def test_replicated_merge_tree(self):
        spec = replicated_merge_tree("/zk/path", "r1", "ver")
        assert spec.name == "ReplicatedMergeTree"
        assert spec.zookeeper_path == "/zk/path"
        assert spec.replica_name == "r1"
        assert spec.args == ("ver",)

    def test_summing_merge_tree(self):
        spec = summing_merge_tree("col1", "col2")
        assert spec.name == "SummingMergeTree"
        assert spec.args == ("col1", "col2")

    def test_aggregating_merge_tree(self):
        spec = aggregating_merge_tree()
        assert spec.name == "AggregatingMergeTree"
