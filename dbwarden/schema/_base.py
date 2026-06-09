from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any


@dataclass
class DBWardenMeta:
    comment: str | None = None
    indexes: list[Any] = dc_field(default_factory=list)
    checks: list[Any] = dc_field(default_factory=list)
    uniques: list[Any] = dc_field(default_factory=list)
    partition: Any = None
    backend_table: Any = None
    pg_indexes: list[Any] = dc_field(default_factory=list)
    pg_checks: list[Any] = dc_field(default_factory=list)
    pg_uniques: list[Any] = dc_field(default_factory=list)
    pg_excludes: list[Any] = dc_field(default_factory=list)
    my_indexes: list[Any] = dc_field(default_factory=list)
    sq_indexes: list[Any] = dc_field(default_factory=list)
    table_attrs: dict[str, Any] = dc_field(default_factory=dict)


def attach_meta(cls, incoming: DBWardenMeta) -> None:
    existing: DBWardenMeta | None = getattr(cls, "__dbwarden_meta__", None)
    if existing is None:
        cls.__dbwarden_meta__ = incoming
        return

    for list_field in (
        "indexes",
        "checks",
        "uniques",
        "pg_indexes",
        "pg_checks",
        "pg_uniques",
        "pg_excludes",
        "my_indexes",
        "sq_indexes",
    ):
        getattr(existing, list_field).extend(getattr(incoming, list_field))

    for scalar_field in ("partition", "backend_table", "comment"):
        value = getattr(incoming, scalar_field)
        if value is not None:
            setattr(existing, scalar_field, value)

    existing.table_attrs.update(incoming.table_attrs)


def read_meta(cls) -> DBWardenMeta | None:
    return getattr(cls, "__dbwarden_meta__", None)
