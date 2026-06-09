from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dbwarden.schema.index import PgIndexSpec


@dataclass
class PgTableSpec:
    tablespace: str | None = None
    fillfactor: int | None = None
    unlogged: bool = False
    inherits: list[str] | None = None


def pg_index(
    name: str,
    columns: list[str],
    *,
    unique: bool = False,
    using: str | None = None,
    where: str | None = None,
    include: list[str] | None = None,
    with_params: dict[str, Any] | None = None,
    tablespace: str | None = None,
    nulls_not_distinct: bool = False,
    column_sorting: dict[str, str] | None = None,
    concurrently: bool = True,
) -> PgIndexSpec:
    return PgIndexSpec(
        name=name, columns=columns, unique=unique, using=using,
        where=where, include=include, with_params=with_params,
        tablespace=tablespace, nulls_not_distinct=nulls_not_distinct,
        column_sorting=column_sorting, concurrently=concurrently,
    )


__all__ = [
    "PgTableSpec",
    "PgIndexSpec",
    "pg_index",
]
