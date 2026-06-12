from __future__ import annotations

from typing import Any

from dbwarden.seed import SeedRow, Seed, seed_data, SeedMeta, _seed_registry, SeedError


class DBWardenSeed(SeedMeta):
    pass


__all__ = ["SeedRow", "seed_data", "DBWardenSeed", "Seed"]
