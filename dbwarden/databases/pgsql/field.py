from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PgFieldSpec:
    collation: str | None = None
    storage: str | None = None
    compression: str | None = None
    generated: str | None = None
    identity: str | None = None
    identity_start: int | None = None
    identity_increment: int | None = None
    identity_min: int | None = None
    identity_max: int | None = None

    def to_col_info(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.collation is not None:
            d["pg_collation"] = self.collation
        if self.storage is not None:
            d["pg_storage"] = self.storage
        if self.compression is not None:
            d["pg_compression"] = self.compression
        if self.generated is not None:
            d["pg_generated"] = self.generated
        if self.identity is not None:
            d["pg_identity"] = self.identity
        if self.identity_start is not None:
            d["pg_identity_start"] = self.identity_start
        if self.identity_increment is not None:
            d["pg_identity_increment"] = self.identity_increment
        if self.identity_min is not None:
            d["pg_identity_min"] = self.identity_min
        if self.identity_max is not None:
            d["pg_identity_max"] = self.identity_max
        return d


def field(
    *,
    collation: str | None = None,
    storage: str | None = None,
    compression: str | None = None,
    generated: str | None = None,
    identity: str | None = None,
    identity_start: int | None = None,
    identity_increment: int | None = None,
    identity_min: int | None = None,
    identity_max: int | None = None,
) -> PgFieldSpec:
    return PgFieldSpec(
        collation=collation,
        storage=storage,
        compression=compression,
        generated=generated,
        identity=identity,
        identity_start=identity_start,
        identity_increment=identity_increment,
        identity_min=identity_min,
        identity_max=identity_max,
    )
