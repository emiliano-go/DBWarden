from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Literal


@dataclass
class DictSpec:
    """Typed spec for a ClickHouse dictionary in ``class Meta``.

    Attributes:
        layout: Dictionary layout function, e.g. ``"flat()"``, ``"hashed()"``,
            ``"complex_key_hashed()"``.
        source: Dictionary source definition, e.g.
            ``{"clickhouse": {"table": "src"}}`` or a SQL string.
        lifetime: Cache lifetime in seconds, or a ``"MIN .. MAX"`` range string.
        primary_key: Primary key column(s) for the dictionary.
    """
    layout: str
    source: dict[str, Any] | str
    lifetime: int | str | None = None
    primary_key: str | list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "ch_dict_layout": self.layout,
            "ch_dict_source": self.source,
        }
        if self.lifetime is not None:
            d["ch_dict_lifetime"] = self.lifetime
        if self.primary_key is not None:
            d["ch_dict_primary_key"] = self.primary_key
        return d


def dictionary(
    *,
    layout: str,
    source: dict[str, Any] | str,
    lifetime: int | str | None = None,
    primary_key: str | list[str] | None = None,
) -> DictSpec:
    """Declare a ClickHouse dictionary.

    Returns a ``DictSpec`` which can be used directly in ``class Meta`` or
    converted to a config dict via ``.to_dict()``.
    """
    return DictSpec(layout=layout, source=source, lifetime=lifetime, primary_key=primary_key)
