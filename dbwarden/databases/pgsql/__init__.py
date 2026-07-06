from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from dbwarden.databases.pgsql.field import PgFieldSpec, field

from dbwarden.databases.pgsql.index import PgIndexSpec, index

from dbwarden.databases.pgsql.constraint import ExcludeSpec, exclude

from dbwarden.databases.pgsql.partition import partition_by_hash, partition_by_list, partition_by_range

from dbwarden.schema.table_meta import PGColumnMeta, PGTableMeta, PGViewMeta

import sys as _sys
pg = _sys.modules[__name__]
@dataclass
class PgTableSpec:
    tablespace: str | None = None
    fillfactor: int | None = None
    unlogged: bool = False
    inherits: list[str] | None = None
    schema: str | None = None
    partition: dict | None = None


@dataclass
class PgViewSpec:
    query: str | None = None
    materialized: bool = False
    schema: str | None = None
    auto_refresh: bool = False


__all__ = [
    "ExcludeSpec",
    "PGColumnMeta",
    "PGTableMeta",
    "PGViewMeta",
    "PgFieldSpec",
    "PgIndexSpec",
    "PgTableSpec",
    "PgViewSpec",
    "exclude",
    "field",
    "index",
    "partition_by_hash",
    "partition_by_list",
    "partition_by_range",
    "pg",
]
