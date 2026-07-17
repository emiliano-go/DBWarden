from __future__ import annotations

from dataclasses import dataclass, field as dc_field


@dataclass(frozen=True)
class NamedCollectionSpec:
    name: str
    entries: dict[str, str] = dc_field(default_factory=dict)
    overridable: dict[str, bool] | None = None

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "entries": dict(self.entries)}
        if self.overridable:
            d["overridable"] = dict(self.overridable)
        return d


def named_collection(
    name: str,
    *,
    overridable: dict[str, bool] | None = None,
    **entries: str,
) -> NamedCollectionSpec:
    return NamedCollectionSpec(name=name, entries=entries, overridable=overridable)
