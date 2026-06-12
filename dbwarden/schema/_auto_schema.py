from __future__ import annotations

from typing import Any, Callable, TypeVar, overload

from dbwarden.schema._meta_reader import apply_meta

try:
    from schemap import SchemaConfig as _SchemaConfig, auto_schema as _schemap_auto_schema
except ImportError:
    _schemap_auto_schema = None
    _SchemaConfig = None


def SchemaConfig(*args: Any, **kwargs: Any) -> Any:
    """Re-exported from schemap. Raises ImportError if schemap is not installed."""
    if _SchemaConfig is None:
        raise ImportError(
            "schemap is required for SchemaConfig. Install it with: pip install schemap"
        )
    return _SchemaConfig(*args, **kwargs)


T = TypeVar("T")

__all__ = ["auto_schema", "SchemaConfig"]


@overload
def auto_schema(cls: type[T]) -> type[T]: ...


@overload
def auto_schema(
    cls: None = None,
    *,
    config: Any = None,
) -> Callable[[type[T]], type[T]]: ...


def auto_schema(cls=None, *, config=None):
    """
    Generate Pydantic schemas from a SQLAlchemy model.

    Reads class Meta, populates column.info, infers SchemaConfig from
    public/private annotations, then calls schemap.auto_schema.

    Generates: Model.Schema, Model.CreateSchema, Model.UpdateSchema,
    Model.PublicSchema.
    """
    if _schemap_auto_schema is None:
        raise ImportError(
            "schemap is required for @auto_schema. Install it with: pip install schemap"
        )

    def _apply(klass: type[T]) -> type[T]:
        apply_meta(klass)
        effective_config = config or _infer_schema_config(klass)
        klass = _schemap_auto_schema(klass, config=effective_config)
        _merge_dbwarden_into_schemas(klass)
        return klass

    if cls is not None:
        return _apply(cls)
    return _apply


def _infer_schema_config(cls: type) -> SchemaConfig:
    exclude_public = []
    exclude_always = []
    for col in cls.__table__.columns:
        if col.name.startswith("_"):
            exclude_always.append(col.name)
        elif col.info.get("dw_public") is False:
            exclude_public.append(col.name)
    return SchemaConfig(exclude_public=exclude_public, exclude_always=exclude_always)


def _merge_dbwarden_into_schemas(cls: type) -> None:
    try:
        from pydantic import BaseModel
    except ImportError:
        return

    for schema_attr in ["Schema", "CreateSchema", "UpdateSchema", "PublicSchema"]:
        schema_cls = getattr(cls, schema_attr, None)
        if schema_cls is None or not issubclass(schema_cls, BaseModel):
            continue
        for field_name, field_info in schema_cls.model_fields.items():
            sa_col = cls.__table__.c.get(field_name)
            if sa_col is None:
                continue
            if "dw_comment" in sa_col.info:
                field_info.description = sa_col.info["dw_comment"]
            backend_meta = {
                k: v for k, v in sa_col.info.items()
                if k.startswith("pg_") or k.startswith("ch_")
                or k.startswith("my_") or k.startswith("mdb_")
                or k.startswith("sq_")
            }
            if backend_meta:
                field_info.json_schema_extra = {
                    **(field_info.json_schema_extra or {}),
                    "dbwarden_backend_meta": backend_meta,
                }
