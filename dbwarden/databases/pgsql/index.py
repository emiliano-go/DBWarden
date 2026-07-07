from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PgIndexSpec:
    """Typed spec for a PostgreSQL index in ``class Meta``.

    Example::

        from dbwarden import PgIndexSpec

        class Meta(PGTableMeta):
            pg_indexes = [
                PgIndexSpec("ix_users_email", ["email"],
                    unique=True, using="gin"),
            ]
    """
    name: str
    columns: list[str]
    unique: bool = False
    using: str | None = None
    where: str | None = None
    include: list[str] | None = None
    with_params: dict[str, Any] | None = None
    tablespace: str | None = None
    nulls_not_distinct: bool = False
    column_sorting: dict[str, str] | None = None
    postgresql_ops: dict[str, str] | None = None
    concurrently: bool = True
    expression: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"name": self.name, "columns": list(self.columns)}
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
        if self.postgresql_ops is not None:
            d["postgresql_ops"] = dict(self.postgresql_ops)
        if not self.concurrently:
            d["concurrently"] = False
        if self.expression is not None:
            d["expression"] = self.expression
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PgIndexSpec:
        return cls(
            name=d["name"],
            columns=list(d.get("columns", [])),
            unique=bool(d.get("unique", False)),
            using=d.get("using"),
            where=d.get("where"),
            include=d.get("include"),
            with_params=d.get("with_params"),
            tablespace=d.get("tablespace"),
            nulls_not_distinct=bool(d.get("nulls_not_distinct", False)),
            column_sorting=d.get("column_sorting"),
            postgresql_ops=d.get("postgresql_ops"),
            concurrently=bool(d.get("concurrently", True)),
            expression=d.get("expression"),
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
    postgresql_ops: dict[str, str] | None = None,
    concurrently: bool = True,
    expression: str | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {"name": name, "columns": list(columns)}
    if unique:
        d["unique"] = True
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
    if postgresql_ops is not None:
        d["postgresql_ops"] = dict(postgresql_ops)
    if not concurrently:
        d["concurrently"] = False
    if expression is not None:
        d["expression"] = expression
    return d
