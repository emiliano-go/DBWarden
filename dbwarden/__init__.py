from importlib.metadata import version

from dbwarden.config_registry import database_config
from dbwarden.schema.table_meta import (
    CHColumnMeta,
    CHTableMeta,
    PGColumnMeta,
    PGTableMeta,
    TableMeta,
)

__version__ = version("dbwarden")

__all__ = [
    "__version__",
    "CHColumnMeta",
    "CHTableMeta",
    "database_config",
    "PGColumnMeta",
    "PGTableMeta",
    "TableMeta",
]
