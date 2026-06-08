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
) -> dict[str, Any]:
    """Build an index dict for ``class Meta``.

    Returns a plain dict — no import needed beyond ``from dbwarden.schema import index``.
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
    return d
