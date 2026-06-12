from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.schema.mysql.field import MyFieldSpec, field


@dataclass
class MyTableSpec:
    engine: str = "InnoDB"
    charset: str = "utf8mb4"
    collate: str = "utf8mb4_unicode_ci"
    row_format: str | None = None
    auto_increment: int | None = None


__all__ = [
    "MyFieldSpec",
    "MyTableSpec",
    "field",
]
