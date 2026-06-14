from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExcludeSpec:
    name: str | None = None
    using: str = "gist"
    where: str | None = None
    elements: list[dict[str, Any]] | None = None


def exclude(
    name: str,
    *,
    using: str = "gist",
    where: str | None = None,
    elements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {"name": name, "using": using}
    if where is not None:
        d["where"] = where
    if elements is not None:
        d["elements"] = list(elements)
    return d
