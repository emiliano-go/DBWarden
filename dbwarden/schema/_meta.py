from __future__ import annotations


class FieldMeta:
    """Documentation/type surface for ``class Meta`` field attributes.

    Users do not need to inherit from this class. DBWarden reads plain inner
    classes by attribute name only.
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

    ch_codec: str | None = None
    ch_default_expression: str | None = None
    ch_materialized: str | None = None
    ch_alias: str | None = None
    ch_ttl: str | None = None
    ch_low_cardinality: bool = False
    ch_nullable: bool = False

    my_charset: str | None = None
    my_collate: str | None = None
    my_unsigned: bool = False
    my_on_update: str | None = None

    mdb_invisible: bool = False
    mdb_without_overlaps: bool = False
    mdb_sequence: str | None = None

    sq_generated: str | None = None
    sq_generated_mode: str = "STORED"
