from __future__ import annotations

from dataclasses import dataclass

from dbwarden.schema.mariadb.field import MdbFieldSpec, field
from dbwarden.schema.mysql import MyTableSpec


@dataclass
class MdbTableSpec(MyTableSpec):
    page_compressed: bool = False
    page_compression_level: int | None = None


__all__ = [
    "MdbFieldSpec",
    "MdbTableSpec",
    "field",
]
