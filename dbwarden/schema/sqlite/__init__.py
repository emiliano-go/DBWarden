from __future__ import annotations

from dataclasses import dataclass

from dbwarden.schema.sqlite.field import SqFieldSpec, field


@dataclass
class SqTableSpec:
    without_rowid: bool = False
    strict: bool = False


__all__ = [
    "SqFieldSpec",
    "SqTableSpec",
    "field",
]
