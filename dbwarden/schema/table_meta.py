from __future__ import annotations

from typing import Any


class TableMeta:
    """Base for all backend-specific table Meta classes.

    Users may inherit from this (or any backend-specific subclass) in their
    ``class Meta`` to get IDE autocomplete for supported attributes.
    """
    comment: str | None = None
    indexes: list[Any] = []
    checks: list[Any] = []
    uniques: list[Any] = []


class PGTableMeta(TableMeta):
    """PostgreSQL table-level metadata; inherit in ``class Meta`` for autocomplete."""
    comment: str | None = None
    pg_fillfactor: int | None = None
    pg_tablespace: str | None = None
    pg_inherits: str | None = None
    pg_unlogged: bool = False
    pg_checks: list[dict[str, Any]] = []
    pg_uniques: list[dict[str, Any]] = []
    pg_excludes: list[dict[str, Any]] = []
    pg_indexes: list[Any] = []
    pg_partition: dict[str, Any] | None = None


from dbwarden.schema._meta import FieldMeta


class PGColumnMeta(FieldMeta):
    """PostgreSQL column-level metadata; inherit in ``Meta`` inner classes for autocomplete.

    Example::

        class Meta(PGTableMeta):
            class id(PGColumnMeta):
                comment = "Surrogate primary key"
                pg_identity = "always"
                pg_storage = "PLAIN"
    """


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


class CHColumnMeta(FieldMeta):
    """ClickHouse column-level metadata; inherit in ``Meta`` inner classes for autocomplete.

    Example::

        class Meta(CHTableMeta):
            class payload(CHColumnMeta):
                comment = "HTTP request body"
                ch_codec = "ZSTD(3)"
                ch_nullable = True
    """
