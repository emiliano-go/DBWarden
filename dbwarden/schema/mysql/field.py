from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MyFieldSpec:
    charset: str | None = None
    collate: str | None = None
    unsigned: bool = False
    on_update: str | None = None

    def to_col_info(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.charset is not None:
            d["my_charset"] = self.charset
        if self.collate is not None:
            d["my_collate"] = self.collate
        if self.unsigned:
            d["my_unsigned"] = True
        if self.on_update is not None:
            d["my_on_update"] = self.on_update
        return d


def field(
    *,
    charset: str | None = None,
    collate: str | None = None,
    unsigned: bool = False,
    on_update: str | None = None,
) -> MyFieldSpec:
    return MyFieldSpec(
        charset=charset,
        collate=collate,
        unsigned=unsigned,
        on_update=on_update,
    )
