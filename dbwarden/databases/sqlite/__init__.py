from __future__ import annotations

from dataclasses import dataclass

from dbwarden.databases.sqlite.field import SqFieldSpec, field

import sys as _sys
sq = _sys.modules[__name__]


@dataclass
class SqTableSpec:
    without_rowid: bool = False
    strict: bool = False


SqTableMeta = SqTableSpec


__all__ = [
    "SqFieldSpec",
    "SqTableMeta",
    "SqTableSpec",
    "field",
    "sq",
]
