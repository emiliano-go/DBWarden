from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SqTableSpec:
    without_rowid: bool = False
    strict: bool = False


__all__ = [
    "SqTableSpec",
]
