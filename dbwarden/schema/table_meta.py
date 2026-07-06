from __future__ import annotations

from typing import Any

from dbwarden.schema._base import _MetaValidator


class TableMeta(metaclass=_MetaValidator):
    """Base for all backend-specific table Meta classes.

    Users may inherit from this (or any backend-specific subclass) in their
    ``class Meta`` to get IDE autocomplete for supported attributes.
    """
    __meta_root__ = True

    comment: str | None = None
    indexes: list[Any] = []
    checks: list[Any] = []
    uniques: list[Any] = []
    primary_key: list[str] = []


class PGTableMeta(TableMeta):
    """PostgreSQL table-level metadata; inherit in ``class Meta`` for autocomplete."""
    comment: str | None = None
    pg_schema: str | None = None
    pg_fillfactor: int | None = None
    pg_tablespace: str | None = None
    pg_inherits: str | None = None
    pg_unlogged: bool = False
    pg_checks: list[dict[str, Any]] = []
    pg_uniques: list[dict[str, Any]] = []
    pg_excludes: list[dict[str, Any]] = []
    pg_indexes: list[Any] = []
    pg_partition: dict[str, Any] | None = None
    pg_rls: bool = False
    pg_rls_force: bool = False
    pg_policies: list[dict[str, Any]] = []
    pg_grants: list[dict[str, Any]] = []
    pg_storage_params: dict[str, Any] | None = None


class PGColumnMeta(metaclass=_MetaValidator):
    """PostgreSQL column-level metadata; inherit in ``Meta`` inner classes for autocomplete.

    Example::

        class Meta(PGTableMeta):
            class id(PGColumnMeta):
                comment = "Surrogate primary key"
                pg = pg.field(identity="always", storage="PLAIN")
    """
    __meta_root__ = True
    comment: str | None = None
    public: bool | None = None
    pg: Any = None


class PGViewMeta(TableMeta):
    """PostgreSQL view-level metadata; inherit in ``class Meta`` for autocomplete.

    Views use ``create or replace view`` semantics. Materialized views
    additionally support ``with data`` / ``with no data`` on creation.

    Example::

        class Meta(PGViewMeta):
            pg_view_query = "SELECT id, name FROM users WHERE active = true"
            pg_view_materialized = False
            pg_schema = "app"
    """
    pg_view_query: str | None = None
    pg_view_materialized: bool = False
    pg_view_auto_refresh: bool = False
    pg_schema: str | None = None


class CHTableMeta(TableMeta):
    """ClickHouse table-level metadata; inherit in ``class Meta``.

    All table options use ``ch_*`` typed attributes. Skip indexes use the
    dedicated ``ch_indexes`` field with ``ChIndexSpec``.

    Example::

        from dbwarden import ChIndexSpec

        class Meta(CHTableMeta):
            ch_engine = ChEngineSpec("MergeTree")
            ch_order_by = ["id", "created_at"]
            ch_partition_by = "toYYYYMM(created_at)"
            ch_indexes = [
                ChIndexSpec("ix_payload", ["payload"],
                    type="bloom_filter", granularity=1),
            ]
    """
    comment: str | None = None
    indexes: list[Any] = []
    checks: list[Any] = []
    uniques: list[Any] = []
    ch_indexes: list[Any] = []

    ch_engine: Any = None
    ch_order_by: str | list[str] | None = None
    ch_primary_key: str | list[str] | None = None
    ch_partition_by: str | None = None
    ch_sample_by: str | None = None
    ch_ttl: list[str] | None = None
    ch_settings: dict[str, str] | None = None

    ch_object_type: str | None = None

    ch_select_statement: str | None = None
    ch_to_table: str | None = None

    ch_dictionary: bool = False
    ch_dict_layout: str | None = None
    ch_dict_source: str | None = None
    ch_dict_lifetime: str | int | None = None
    ch_dict_primary_key: str | list[str] | None = None

    ch_projections: list[Any] = []

    ch_zookeeper_path: str | None = None
    ch_replica_name: str | None = None


class CHColumnMeta(metaclass=_MetaValidator):
    """ClickHouse column-level metadata; inherit in ``Meta`` inner classes for autocomplete.

    Example::

        class Meta(CHTableMeta):
            class payload(CHColumnMeta):
                comment = "HTTP request body"
                ch = ch.field(codec="ZSTD(3)", nullable=True)
    """
    __meta_root__ = True
    comment: str | None = None
    public: bool | None = None
    ch: Any = None


class MyTableMeta(TableMeta):
    """MySQL table-level metadata; inherit in ``class Meta``."""

    comment: str | None = None
    indexes: list[Any] = []
    checks: list[Any] = []
    uniques: list[Any] = []

    my_engine: str | None = None
    my_charset: str | None = None
    my_collate: str | None = None
    my_row_format: str | None = None
    my_auto_increment: int | None = None
    my_indexes: list[Any] = []
    my_checks: list[dict[str, Any]] = []
    my_uniques: list[dict[str, Any]] = []


class MyColumnMeta(metaclass=_MetaValidator):
    """MySQL column-level metadata; inherit in ``Meta`` inner classes.

    Example::

        class Meta(MyTableMeta):
            class id(MyColumnMeta):
                my = my.field(unsigned=True)
    """
    __meta_root__ = True
    comment: str | None = None
    public: bool | None = None
    my: Any = None


class MdbTableMeta(MyTableMeta):
    """MariaDB table-level metadata; inherit in ``class Meta``."""

    mdb_page_compressed: bool = False
    mdb_page_compression_level: int | None = None


class MdbColumnMeta(metaclass=_MetaValidator):
    """MariaDB column-level metadata; inherit in ``Meta`` inner classes."""
    __meta_root__ = True
    comment: str | None = None
    public: bool | None = None
    mdb: Any = None
