from __future__ import annotations

from typing import Any

from dbwarden.exceptions import DBWardenConfigError
from dbwarden.schema._base import DBWardenMeta, attach_meta


_LIST_FIELDS = {
    "indexes",
    "checks",
    "uniques",
    "pg_indexes",
    "pg_checks",
    "pg_uniques",
    "pg_excludes",
    "my_indexes",
    "sq_indexes",
    "pg_inherits",
}


def apply_meta(cls: type) -> None:
    """Read ``class Meta`` from a mapped model and populate DBWarden metadata."""
    if getattr(cls, "__dbwarden_meta_applied__", False):
        return

    meta_chain = _collect_meta_chain(cls)
    if not meta_chain:
        return

    if hasattr(cls, "__table__"):
        for col in cls.__table__.columns:
            if col.info:
                raise DBWardenConfigError(
                    f"Column '{cls.__tablename__}.{col.name}' has non-empty .info before "
                    f"DBWarden metadata injection. Do not use mapped_column(info=...) - "
                    f"declare field metadata in class Meta instead."
                )

    merged_table: dict[str, Any] = {}
    merged_fields: dict[str, dict[str, Any]] = {}

    for meta_cls in reversed(meta_chain):
        _merge_meta_class(meta_cls, merged_table, merged_fields)

    if hasattr(cls, "__table__"):
        column_names = {c.name for c in cls.__table__.columns}
        for field_name, attrs in merged_fields.items():
            if field_name not in column_names:
                continue
            _write_column_info(cls.__table__.c[field_name], attrs)

    attach_meta(cls, _build_dbwarden_meta(merged_table))
    cls.__dbwarden_meta_applied__ = True


def _collect_meta_chain(cls: type) -> list[type]:
    chain: list[type] = []
    for klass in cls.__mro__:
        meta = klass.__dict__.get("Meta")
        if meta is not None and isinstance(meta, type):
            chain.append(meta)
    return chain


def _merge_meta_class(
    meta_cls: type,
    merged_table: dict[str, Any],
    merged_fields: dict[str, dict[str, Any]],
) -> None:
    for name, value in vars(meta_cls).items():
        if name.startswith("__"):
            continue
        if isinstance(value, type):
            field_attrs = merged_fields.setdefault(name, {})
            for attr, attr_value in vars(value).items():
                if attr.startswith("__"):
                    continue
                field_attrs[attr] = attr_value
            continue

        if callable(value):
            continue

        if name in _LIST_FIELDS and isinstance(value, list):
            merged_table[name] = list(merged_table.get(name, [])) + value
        else:
            merged_table[name] = value


def _write_column_info(col, attrs: dict[str, Any]) -> None:
    for attr, value in attrs.items():
        if value is None or value is False:
            continue
        if attr == "comment":
            col.info["dw_comment"] = value
        elif attr == "public":
            col.info["dw_public"] = value
        else:
            col.info[attr] = value


def _build_dbwarden_meta(table_attrs: dict[str, Any]) -> DBWardenMeta:
    meta = DBWardenMeta()
    meta.comment = table_attrs.get("comment")
    meta.indexes = list(table_attrs.get("indexes", []))
    meta.checks = list(table_attrs.get("checks", []))
    meta.uniques = list(table_attrs.get("uniques", []))
    meta.partition = table_attrs.get("partition") or table_attrs.get("pg_partition")
    meta.pg_indexes = list(table_attrs.get("pg_indexes", []))
    meta.pg_checks = list(table_attrs.get("pg_checks", []))
    meta.pg_uniques = list(table_attrs.get("pg_uniques", []))
    meta.pg_excludes = list(table_attrs.get("pg_excludes", []))
    meta.my_indexes = list(table_attrs.get("my_indexes", []))
    meta.sq_indexes = list(table_attrs.get("sq_indexes", []))
    meta.table_attrs = dict(table_attrs)

    backend_table: dict[str, Any] = {}
    for key, value in table_attrs.items():
        if key.startswith(("pg_", "ch_", "my_", "mdb_", "sq_")):
            backend_table[key] = value

    if backend_table:
        meta.backend_table = backend_table

    return meta
