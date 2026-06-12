from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SqFieldSpec:
    generated: str | None = None
    generated_mode: str = "STORED"

    def to_col_info(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.generated is not None:
            d["sq_generated"] = self.generated
        if self.generated_mode != "STORED":
            d["sq_generated_mode"] = self.generated_mode
        return d


def field(
    *,
    generated: str | None = None,
    generated_mode: str = "STORED",
) -> SqFieldSpec:
    return SqFieldSpec(
        generated=generated,
        generated_mode=generated_mode,
    )
