from __future__ import annotations

from typing import Any


def dictionary(
    *,
    layout: str,
    source: str,
    lifetime: str | int | None = None,
    primary_key: str | list[str] | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "ch_dict_layout": layout,
        "ch_dict_source": source,
    }
    if lifetime is not None:
        d["ch_dict_lifetime"] = lifetime
    if primary_key is not None:
        d["ch_dict_primary_key"] = primary_key
    return d
