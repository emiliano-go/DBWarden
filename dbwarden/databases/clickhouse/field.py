from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ChFieldSpec:
    codec: str | None = None
    default_expression: str | None = None
    materialized: str | None = None
    alias: str | None = None
    ephemeral: str | None = None
    ttl: str | None = None
    low_cardinality: bool = False
    nullable: bool = False
    type: str | None = None

    def to_col_info(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.codec is not None:
            d["ch_codec"] = self.codec
        if self.default_expression is not None:
            d["ch_default_expression"] = self.default_expression
        if self.materialized is not None:
            d["ch_materialized"] = self.materialized
        if self.alias is not None:
            d["ch_alias"] = self.alias
        if self.ephemeral is not None:
            d["ch_ephemeral"] = self.ephemeral
        if self.ttl is not None:
            d["ch_ttl"] = self.ttl
        if self.low_cardinality:
            d["ch_low_cardinality"] = True
        if self.nullable:
            d["ch_nullable"] = True
        if self.type is not None:
            d["ch_type"] = self.type
        return d


def field(
    *,
    codec: str | None = None,
    default_expression: str | None = None,
    materialized: str | None = None,
    alias: str | None = None,
    ephemeral: str | None = None,
    ttl: str | None = None,
    low_cardinality: bool = False,
    nullable: bool = False,
    type: str | None = None,
) -> ChFieldSpec:
    return ChFieldSpec(
        codec=codec,
        default_expression=default_expression,
        materialized=materialized,
        alias=alias,
        ephemeral=ephemeral,
        ttl=ttl,
        low_cardinality=low_cardinality,
        nullable=nullable,
        type=type,
    )
