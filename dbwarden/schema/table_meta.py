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
    """PostgreSQL table-level metadata — inherit in ``class Meta`` for autocomplete."""
    comment: str | None = None
    pg_fillfactor: int | None = None
    pg_tablespace: str | None = None
    pg_inherits: str | None = None
    pg_checks: list[dict[str, Any]] = []
    pg_uniques: list[dict[str, Any]] = []
    pg_excludes: list[dict[str, Any]] = []
    pg_indexes: list[dict[str, Any]] = []


class PGColumnMeta:
    """PostgreSQL column-level metadata — inherit in ``Meta`` inner classes for autocomplete.

    Example::

        class Meta(PGTableMeta):
            class id(PGColumnMeta):
                comment = "Surrogate primary key"
                pg_identity = "always"
                pg_storage = "PLAIN"
    """
    comment: str | None = None
    public: bool | None = None
    pg_collation: str | None = None
    pg_storage: str | None = None
    pg_compression: str | None = None
    pg_generated: str | None = None
    pg_identity: str | None = None
    pg_identity_start: int | None = None
    pg_identity_increment: int | None = None
    pg_identity_min: int | None = None
    pg_identity_max: int | None = None


class CHTableMeta(TableMeta):
    """ClickHouse table-level metadata — inherit in ``class Meta`` for autocomplete."""
    comment: str | None = None
    ch_engine: str | tuple | list | None = None
    ch_order_by: str | list[str] | None = None
    ch_partition_by: str | None = None
    ch_sample_by: str | None = None
    ch_ttl: list[str] | None = None
    ch_indexes: list[dict[str, Any]] = []
    ch_zookeeper_path: str | None = None
    ch_replica_name: str | None = None
    ch_projections: list[dict[str, str]] = []


class CHColumnMeta:
    """ClickHouse column-level metadata — inherit in ``Meta`` inner classes for autocomplete."""
    comment: str | None = None
    ch_codec: str | None = None
    ch_default_expression: str | None = None
    ch_materialized: str | None = None
    ch_alias: str | None = None
    ch_ttl: str | None = None
    ch_low_cardinality: bool = False
    ch_nullable: bool = False
