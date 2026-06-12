from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MdbFieldSpec:
    invisible: bool = False
    without_overlaps: bool = False
    sequence: str | None = None

    def to_col_info(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.invisible:
            d["mdb_invisible"] = True
        if self.without_overlaps:
            d["mdb_without_overlaps"] = True
        if self.sequence is not None:
            d["mdb_sequence"] = self.sequence
        return d


def field(
    *,
    invisible: bool = False,
    without_overlaps: bool = False,
    sequence: str | None = None,
) -> MdbFieldSpec:
    return MdbFieldSpec(
        invisible=invisible,
        without_overlaps=without_overlaps,
        sequence=sequence,
    )
