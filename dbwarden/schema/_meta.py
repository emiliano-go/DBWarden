from __future__ import annotations

from typing import Any

from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema._base import _MetaValidator


class FieldMeta(metaclass=_MetaValidator):
    """Cross-database field metadata for ``class Meta`` inner classes.

    Users should inherit from a backend-specific subclass (e.g. ``PGColumnMeta``,
    ``CHColumnMeta``) to get IDE autocomplete for supported attributes.
    """
    __meta_root__ = True

    comment: str | None = None
    public: bool | None = None


class PGFieldMeta(FieldMeta):
    """PostgreSQL field metadata.

    Use ``pg = pg.field(...)`` to set column-level options.
    """
    pg: Any = None


class CHFieldMeta(FieldMeta):
    """ClickHouse field metadata.

    Use ``ch = ch.field(...)`` to set column-level options.
    """
    ch: Any = None


class MyFieldMeta(FieldMeta):
    """MySQL field metadata.

    Use ``my = my.field(...)`` to set column-level options.
    """
    my: Any = None


class MdbFieldMeta(FieldMeta):
    """MariaDB field metadata.

    Use ``mdb = mdb.field(...)`` to set column-level options.
    """
    mdb: Any = None


class SqFieldMeta(FieldMeta):
    """SQLite field metadata.

    Use ``sq = sq.field(...)`` to set column-level options.
    """
    sq: Any = None
