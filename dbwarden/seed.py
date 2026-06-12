from __future__ import annotations

import hashlib
import inspect
from typing import Any, ClassVar

from dbwarden.exceptions import SeedError


_seed_registry: list[type[Seed]] = []


class SeedRow:
    _data: dict

    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    def to_dict(self) -> dict:
        return dict(self._data)


class SeedMeta:
    database: str
    description: str
    on_conflict: str
    conflict_columns: list[str]
    source_hash: str

    def __init__(
        self,
        database: str,
        description: str,
        on_conflict: str = "ignore",
        conflict_columns: list[str] | None = None,
        source_hash: str = "",
        version: str = "",
        **kwargs: Any,
    ) -> None:
        self.database = database
        self.description = description
        self.on_conflict = on_conflict
        self.conflict_columns = conflict_columns or []
        self.source_hash = source_hash


class Seed:
    model: ClassVar[type]
    rows: ClassVar[list | None] = None
    __seed_meta__: ClassVar[SeedMeta | None] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _seed_registry.append(cls)


def seed_data(
    database: str,
    version: str = "",
    description: str = "",
    on_conflict: str = "ignore",
    conflict_columns: list[str] | None = None,
):
    """Decorator that marks a class as an in-code seed definition.

    Deprecated: Use ``Seed`` base class instead.
    """
    if on_conflict not in ("ignore", "update", "error"):
        raise ValueError(
            f"on_conflict must be 'ignore', 'update', or 'error', got {on_conflict!r}"
        )

    def decorator(cls):
        source = ""
        try:
            source = inspect.getsource(cls)
        except (OSError, TypeError):
            pass
        source_hash = hashlib.sha256(source.encode()).hexdigest()[:16] if source else ""

        cls.__seed_meta__ = SeedMeta(
            database=database,
            description=description,
            on_conflict=on_conflict,
            conflict_columns=conflict_columns or [],
            source_hash=source_hash,
        )
        cls.__dbwarden_seed__ = cls.__seed_meta__
        _seed_registry.append(cls)
        return cls

    return decorator


def _row_to_dict(row: Any, model_cls: type | None = None) -> dict:
    if model_cls is not None and isinstance(row, model_cls):
        return {col.name: getattr(row, col.name) for col in model_cls.__table__.columns}
    if isinstance(row, SeedRow):
        return row.to_dict()
    if isinstance(row, dict):
        return row
    raise SeedError(f"Invalid seed row type: {type(row)}")
