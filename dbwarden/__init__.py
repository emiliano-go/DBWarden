from importlib.metadata import version

from dbwarden.config_registry import database_config
from dbwarden.seed import Seed, SeedRow, seed_data

__version__ = version("dbwarden")

__all__ = [
    "__version__",
    "database_config",
    "Seed",
    "SeedRow",
    "seed_data",
]
