from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ChEngineSpec:
    name: str
    args: tuple[str, ...] = ()
    zookeeper_path: str | None = None
    replica_name: str | None = None
    settings: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.args, str):
            self.args = (self.args,)
        elif not isinstance(self.args, tuple):
            self.args = tuple(self.args)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name}
        if self.args:
            d["args"] = self.args
        if self.zookeeper_path is not None:
            d["zookeeper_path"] = self.zookeeper_path
        if self.replica_name is not None:
            d["replica_name"] = self.replica_name
        if self.settings is not None:
            d["settings"] = dict(self.settings)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ChEngineSpec:
        return cls(
            name=d["name"],
            args=tuple(d.get("args", [])),
            zookeeper_path=d.get("zookeeper_path"),
            replica_name=d.get("replica_name"),
            settings=dict(d.get("settings", {})) if d.get("settings") else None,
        )

    @classmethod
    def from_engine_string(cls, engine_str: str) -> ChEngineSpec:
        name, *rest = engine_str.split("(", 1)
        name = name.strip()
        inner = rest[0].rstrip(")") if rest else ""
        if not inner:
            return cls(name)
        parts = _split_engine_args(inner)
        zk_path = None
        replica = None
        tail_args = list(parts)
        if name.lower().startswith("replicated") or "zookeeper" in name.lower():
            if tail_args:
                zk_path = tail_args.pop(0).strip("'\" ")
            if tail_args:
                replica = tail_args.pop(0).strip("'\" ")
        return cls(name, args=tuple(tail_args), zookeeper_path=zk_path, replica_name=replica)


def _split_engine_args(inner: str) -> list[str]:
    args: list[str] = []
    depth = 0
    current: list[str] = []
    in_quote: str | None = None
    for ch in inner:
        if in_quote:
            current.append(ch)
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            current.append(ch)
            in_quote = ch
        elif ch in ("(", "["):
            depth += 1
            current.append(ch)
        elif ch in (")", "]"):
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    rest = "".join(current).strip()
    if rest:
        args.append(rest)
    return args


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
