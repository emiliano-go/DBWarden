from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class IndexSpec:
    """Typed spec for an index definition in ``class Meta``.

    Example::

        class Meta(TableMeta):
            indexes = [
                index("ix_users_email", ["email"], unique=True),
            ]
    """
    columns: list[str]
    name: str | None = None
    unique: bool = False
    using: str | None = None
    where: str | None = None
    include: list[str] | None = None
    with_params: dict[str, Any] | None = None
    tablespace: str | None = None
    nulls_not_distinct: bool = False
    column_sorting: dict[str, str] | None = None
    comment: str | None = None
    concurrently: bool = True
    clickhouse_type: str | None = None
    clickhouse_granularity: int | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"columns": list(self.columns)}
        if self.name is not None:
            d["name"] = self.name
        if self.unique:
            d["unique"] = True
        if self.using is not None:
            d["using"] = self.using
        if self.where is not None:
            d["where"] = self.where
        if self.include is not None:
            d["include"] = list(self.include)
        if self.with_params is not None:
            d["with_params"] = dict(self.with_params)
        if self.tablespace is not None:
            d["tablespace"] = self.tablespace
        if self.nulls_not_distinct:
            d["nulls_not_distinct"] = True
        if self.column_sorting is not None:
            d["column_sorting"] = dict(self.column_sorting)
        if self.comment is not None:
            d["comment"] = self.comment
        if not self.concurrently:
            d["concurrently"] = False
        if self.clickhouse_type is not None:
            d["clickhouse_type"] = self.clickhouse_type
        if self.clickhouse_granularity is not None:
            d["clickhouse_granularity"] = self.clickhouse_granularity
        return d

    @classmethod
    def from_dict(cls, d: dict) -> IndexSpec:
        return cls(
            columns=list(d.get("columns", [])),
            name=d.get("name"),
            unique=bool(d.get("unique", False)),
            using=d.get("using"),
            where=d.get("where"),
            include=d.get("include"),
            with_params=d.get("with_params"),
            tablespace=d.get("tablespace"),
            nulls_not_distinct=bool(d.get("nulls_not_distinct", False)),
            column_sorting=d.get("column_sorting"),
            comment=d.get("comment"),
            concurrently=bool(d.get("concurrently", True)),
            clickhouse_type=d.get("clickhouse_type"),
            clickhouse_granularity=d.get("clickhouse_granularity"),
        )


def index(
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
    comment: str | None = None,
    concurrently: bool = True,
    clickhouse_type: str | None = None,
    clickhouse_granularity: int | None = None,
) -> dict[str, Any]:
    """Build an index dict for ``class Meta``.

    Returns a plain dict; no import needed beyond ``from dbwarden.schema import index``.
    All fields are optional except *name* and *columns*.
    """
    d: dict[str, Any] = {
        "name": name,
        "columns": list(columns),
        "unique": unique,
    }
    if using is not None:
        d["using"] = using
    if where is not None:
        d["where"] = where
    if include is not None:
        d["include"] = list(include)
    if with_params is not None:
        d["with_params"] = dict(with_params)
    if tablespace is not None:
        d["tablespace"] = tablespace
    if nulls_not_distinct:
        d["nulls_not_distinct"] = True
    if column_sorting is not None:
        d["column_sorting"] = dict(column_sorting)
    if comment is not None:
        d["comment"] = comment
    if not concurrently:
        d["concurrently"] = False
    if clickhouse_type is not None:
        d["clickhouse_type"] = clickhouse_type
    if clickhouse_granularity is not None:
        d["clickhouse_granularity"] = clickhouse_granularity
    return d
