from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.schema.pgsql.field import PgFieldSpec, field
from dbwarden.schema.pgsql.index import PgIndexSpec, index
from dbwarden.schema.pgsql.constraint import ExcludeSpec, exclude
from dbwarden.schema.pgsql.partition import partition_by_hash, partition_by_list, partition_by_range


@dataclass
class PgTableSpec:
    tablespace: str | None = None
    fillfactor: int | None = None
    unlogged: bool = False
    inherits: list[str] | None = None


__all__ = [
    "ExcludeSpec",
    "PgFieldSpec",
    "PgIndexSpec",
    "PgTableSpec",
    "exclude",
    "field",
    "index",
    "partition_by_hash",
    "partition_by_list",
    "partition_by_range",
]
