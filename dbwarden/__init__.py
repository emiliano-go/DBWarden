from importlib.metadata import version

from dbwarden.config_registry import database_config
from dbwarden.schema import (
    CHColumnMeta,
    CHTableMeta,
    ChEngineSpec,
    ChIndexSpec,
    ChTableSpec,
    FieldMeta,
    IndexSpec,
    MdbTableSpec,
    MyTableSpec,
    PGColumnMeta,
    PGTableMeta,
    PgIndexSpec,
    PgTableSpec,
    ProjectionSpec,
    SqTableSpec,
    TableMeta,
)
from dbwarden.schema.engine import ChEngineSpec
from dbwarden.schema.index import ChIndexSpec, PgIndexSpec
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
    "ChIndexSpec",
    "ChTableSpec",
    "database_config",
    "FieldMeta",
    "IndexSpec",
    "MdbTableSpec",
    "MyTableSpec",
    "PGColumnMeta",
    "PGTableMeta",
    "PgIndexSpec",
    "PgTableSpec",
    "ProjectionSpec",
    "SqTableSpec",
    "TableMeta",
]
