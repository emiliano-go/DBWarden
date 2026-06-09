from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from typing import Any


@dataclass
class SeedRow:
    _data: dict

    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    def to_dict(self) -> dict:
        return dict(self._data)


@dataclass
class DBWardenSeed:
    database: str
    version: str
    description: str
    on_conflict: str = "ignore"
    conflict_columns: list[str] | None = None
    source_hash: str = ""

    @property
    def seed_id(self) -> str:
        return f"{self.database}__{self.version}"


def seed_data(
    database: str,
    version: str,
    description: str,
    on_conflict: str = "ignore",
    conflict_columns: list[str] | None = None,
):
    """Decorator that marks a class as an in-code seed definition.

    Args:
        database: Target database name.
        version: Migration version string (e.g. ``"0001"``).
        description: Human-readable description.
        on_conflict: ``"ignore"`` (default), ``"update"``, or ``"error"``.
        conflict_columns: Column names for conflict detection (``on_conflict="update"``).

    The decorated class must have either:
    - A ``rows`` attribute (list of ``SeedRow``) for row-based seeds, or
    - A ``generate(session)`` static method for logic-based seeds.
    """
    if on_conflict not in ("ignore", "update", "error"):
        raise ValueError(f"on_conflict must be 'ignore', 'update', or 'error', got {on_conflict!r}")

    def decorator(cls):
        source = ""
        try:
            source = inspect.getsource(cls)
        except (OSError, TypeError):
            pass
        source_hash = hashlib.sha256(source.encode()).hexdigest()[:16] if source else ""

        cls.__dbwarden_seed__ = DBWardenSeed(
            database=database,
            version=version,
            description=description,
            on_conflict=on_conflict,
            conflict_columns=conflict_columns or [],
            source_hash=source_hash,
        )
        return cls

    return decorator
