from __future__ import annotations

from dataclasses import dataclass

from dbwarden.databases.mariadb.field import MdbFieldSpec, field
from dbwarden.databases.mysql import MyTableSpec
from dbwarden.schema.table_meta import MdbColumnMeta, MdbTableMeta


@dataclass
class MdbTableSpec(MyTableSpec):
    page_compressed: bool = False
    page_compression_level: int | None = None


__all__ = [
    "MdbColumnMeta",
    "MdbFieldSpec",
    "MdbTableMeta",
    "MdbTableSpec",
    "field",
]
