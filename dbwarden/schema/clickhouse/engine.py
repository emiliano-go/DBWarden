from __future__ import annotations

from dbwarden.schema.engine import ChEngineSpec


def merge_tree(
    *,
    settings: dict[str, str] | None = None,
) -> ChEngineSpec:
    return ChEngineSpec("MergeTree", settings=settings)


def replacing_merge_tree(
    version_col: str | None = None,
    *,
    settings: dict[str, str] | None = None,
) -> ChEngineSpec:
    args = (version_col,) if version_col else ()
    return ChEngineSpec("ReplacingMergeTree", args=args, settings=settings)


def replicated_merge_tree(
    zookeeper_path: str,
    replica_name: str,
    *args: str,
    settings: dict[str, str] | None = None,
) -> ChEngineSpec:
    return ChEngineSpec(
        "ReplicatedMergeTree",
        args=args,
        zookeeper_path=zookeeper_path,
        replica_name=replica_name,
        settings=settings,
    )


def summing_merge_tree(
    *columns: str,
    settings: dict[str, str] | None = None,
) -> ChEngineSpec:
    return ChEngineSpec("SummingMergeTree", args=columns, settings=settings)


def aggregating_merge_tree(
    *,
    settings: dict[str, str] | None = None,
) -> ChEngineSpec:
    return ChEngineSpec("AggregatingMergeTree", settings=settings)
