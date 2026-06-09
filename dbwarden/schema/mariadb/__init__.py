from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.schema.mysql import MyTableSpec


@dataclass
class MdbTableSpec(MyTableSpec):
    page_compressed: bool = False
    page_compression_level: int | None = None


__all__ = [
    "MdbTableSpec",
]
