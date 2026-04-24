from importlib.metadata import version

from dbwarden.config_registry import database_config

__version__ = version("dbwarden")

__all__ = ["__version__", "database_config"]
