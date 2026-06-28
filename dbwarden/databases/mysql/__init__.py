from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.databases.mysql.field import MyFieldSpec, field
from dbwarden.schema.table_meta import MyColumnMeta, MyTableMeta

import sys as _sys
my = _sys.modules[__name__]

@dataclass
class MyTableSpec:
    engine: str = "InnoDB"
    charset: str = "utf8mb4"
    collate: str = "utf8mb4_unicode_ci"
    row_format: str | None = None
    auto_increment: int | None = None


__all__ = [
    "MyColumnMeta",
    "MyFieldSpec",
    "MyTableMeta",
    "MyTableSpec",
    "field",
    "my",
]
