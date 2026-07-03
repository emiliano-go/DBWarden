from __future__ import annotations

import typing
from dataclasses import dataclass, field as dc_field
from typing import Any

from dbwarden.exceptions import DBWardenConfigError


class _MetaValidator(type):
    """Metaclass that validates Meta class attribute names at import time.

    Walks the MRO to collect all ``__annotations__`` from ancestor classes,
    then rejects any non-dunder, non-callable, non-class attribute whose name
    does not appear in the collected annotations.

    Root base classes (``FieldMeta``, ``TableMeta``) are exempted via
    ``__meta_root__ = True``.
    """

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        if namespace.get("__meta_root__"):
            return cls

        valid_attrs: set[str] = set()
        for base in cls.__mro__:
            if base is cls:
                continue
            if hasattr(base, "__annotations__"):
                valid_attrs.update(base.__annotations__)

        valid_attrs.update(namespace.get("__annotations__", {}))

        for attr_name, attr_value in list(namespace.items()):
            if attr_name.startswith("__"):
                continue
            if isinstance(attr_value, type):
                continue
            if callable(attr_value):
                continue
            if attr_name not in valid_attrs:
                raise DBWardenConfigError(
                    f"Unknown attribute '{attr_name}' on {name}. "
                    f"Valid attributes: {sorted(valid_attrs)}"
                )

        return cls


@dataclass
class DBWardenMeta:
    comment: str | None = None
    indexes: list[Any] = dc_field(default_factory=list)
    checks: list[Any] = dc_field(default_factory=list)
    uniques: list[Any] = dc_field(default_factory=list)
    primary_key: list[str] = dc_field(default_factory=list)
    partition: Any = None
    backend_table: Any = None
    pg_indexes: list[Any] = dc_field(default_factory=list)
    pg_checks: list[Any] = dc_field(default_factory=list)
    pg_uniques: list[Any] = dc_field(default_factory=list)
    pg_excludes: list[Any] = dc_field(default_factory=list)
    ch_indexes: list[Any] = dc_field(default_factory=list)
    my_indexes: list[Any] = dc_field(default_factory=list)
    my_checks: list[Any] = dc_field(default_factory=list)
    my_uniques: list[Any] = dc_field(default_factory=list)
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
        "primary_key",
        "pg_indexes",
        "pg_checks",
        "pg_uniques",
        "pg_excludes",
        "pg_policies",
        "pg_grants",
        "ch_indexes",
        "my_indexes",
        "my_checks",
        "my_uniques",
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
