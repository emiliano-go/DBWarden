from importlib.metadata import version

from dbwarden.config_registry import database_config
from dbwarden.schema.engine import ChEngineSpec
from dbwarden.schema.projection import ProjectionSpec
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
    "ChEngineSpec",
    "database_config",
    "PGColumnMeta",
    "PGTableMeta",
    "ProjectionSpec",
    "TableMeta",
]
