from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProjectionSpec:
    name: str
    query: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "query": self.query}

    @classmethod
    def from_dict(cls, d: dict) -> ProjectionSpec:
        return cls(name=d["name"], query=d.get("query", ""))


def projection(name: str, query: str) -> dict[str, Any]:
    return {"name": name, "query": query}
