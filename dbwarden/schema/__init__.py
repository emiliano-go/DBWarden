"""Core schema package.

Import concrete helpers from their defining modules or from
``dbwarden.databases`` backend packages.
"""

from dbwarden.seed import SeedMeta


class DBWardenSeed(SeedMeta):
    pass


__all__ = ["DBWardenSeed"]
