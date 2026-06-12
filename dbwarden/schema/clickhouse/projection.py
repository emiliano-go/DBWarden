from __future__ import annotations

from typing import Any


def projection(name: str, query: str) -> dict[str, Any]:
    return {"name": name, "query": query}
