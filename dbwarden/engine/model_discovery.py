import os
import re
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import List, Optional, Type

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base

from dbwarden.database.queries import get_current_dialect
from dbwarden.models import SchemaDifference

Base = declarative_base()


class ModelColumn:
    """Represents a column from a SQLAlchemy model."""

    def __init__(
        self,
        name: str,
        type: str,
        nullable: bool,
        primary_key: bool,
        unique: bool,
        default: Optional[str],
        foreign_key: Optional[str],
        visit_name: Optional[str] = None,
        info: Optional[dict] = None,
    ):
        self.name = name
        self.type = type
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.default = default
        self.foreign_key = foreign_key
        self.visit_name = visit_name
        self.info = info or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "unique": self.unique,
            "default": self.default,
            "foreign_key": self.foreign_key,
            "visit_name": self.visit_name,
            "info": self.info,
        }


class ModelTable:
    """Represents a table from a SQLAlchemy model."""

    def __init__(
        self,
        name: str,
        columns: List[ModelColumn],
        options: Optional[dict] = None,
    ):
        self.name = name
        self.columns = columns
        self.options = options or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": [col.to_dict() for col in self.columns],
            "options": self.options,
        }


def load_model_from_path(filepath: str) -> Optional[ModuleType]:
    """
    Load a SQLAlchemy model from a Python file path.

    Args:
        filepath: Path to the Python file containing SQLAlchemy models.

    Returns:
        The loaded module or None if failed.
    """
    try:
        spec = importlib.util.spec_from_file_location("models", filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module
    except Exception:
        return None


def discover_models_in_directory(directory: str) -> List[str]:
    """
    Discover model files in a directory.

    Args:
        directory: Path to search for model files.

    Returns:
        List of Python file paths that may contain models.
    """
    model_files = []
    directory_path = Path(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        return []

    for filepath in directory_path.rglob("*.py"):
        if filepath.name.startswith("_"):
            continue
        model_files.append(str(filepath))

    return model_files


def get_all_model_tables(
    model_paths: Optional[List[str]] = None,
) -> List[ModelTable]:
    """
    Extract table definitions from SQLAlchemy models.

    Args:
        model_paths: List of paths to model files. If None, auto-discovers in models/ directory.

    Returns:
        List of ModelTable objects representing all tables in the models.
    """
    tables = []
    seen_tables = set()

    if model_paths is None:
        model_paths = auto_discover_model_paths()

    # Ensure project root is in sys.path for proper imports
    cwd = str(Path.cwd().resolve())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Also check parent directories for project roots
    for potential_root in [cwd, str(Path(cwd).parent)]:
        if potential_root not in sys.path:
            sys.path.insert(0, potential_root)

    for model_path in model_paths:
        if not os.path.exists(model_path):
            continue

        if os.path.isdir(model_path):
            model_files = discover_models_in_directory(model_path)
        else:
            model_files = [model_path]

        for model_file in model_files:
            module = load_model_from_path(model_file)
            if module is None:
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and hasattr(attr, "__tablename__")
                    and hasattr(attr, "__table__")
                    and attr.__tablename__ is not None
                ):
                    if attr.__tablename__ in seen_tables:
                        continue
                    seen_tables.add(attr.__tablename__)
                    table = extract_table_from_model(attr)
                    if table:
                        tables.append(table)

    return tables


def auto_discover_model_paths() -> List[str]:
    """
    Auto-discover model paths by looking for models/ or model/ directories.

    Searches:
    1. Current directory for models/ or model/
    2. All subdirectories for models/ or model/ folders
    3. Parent directories (up to 5 levels)
    4. Ignores common lib folders (.venv, node_modules, __pycache__, etc.)

    Returns:
        List of directories that may contain models.
    """
    model_paths = []
    current = Path.cwd().resolve()

    IGNORED_DIRS = {
        ".venv",
        "node_modules",
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        "build",
        "dist",
        "egg-info",
        ".tox",
        ".nox",
        "venv",
        "ENV",
        ".egg",
        ".cache",
        "coverage",
        ".pytest_cache",
        "site-packages",
        "Lib",
        "Scripts",
        "bin",
        "include",
    }

    def find_model_dirs_in(directory: Path) -> List[str]:
        """Find models/ or model/ folders inside a directory."""
        found = []
        try:
            if not directory.exists() or not directory.is_dir():
                return found

            for item in directory.iterdir():
                try:
                    if item.is_dir() and item.name not in IGNORED_DIRS:
                        for model_name in ["models", "model"]:
                            model_dir = item / model_name
                            if model_dir.exists() and model_dir.is_dir():
                                found.append(str(model_dir))
                except PermissionError:
                    continue
        except PermissionError:
            pass
        return found

    for _ in range(5):
        # Check for models/ or model/ in current directory
        for dirname in ["models", "model"]:
            model_dir = current / dirname
            if model_dir.exists() and model_dir.is_dir():
                if str(model_dir) not in model_paths:
                    model_paths.append(str(model_dir))

        # Check all subdirectories for models/model folders
        for subdir in find_model_dirs_in(current):
            if subdir not in model_paths:
                model_paths.append(subdir)

        if current.parent == current:
            break
        current = current.parent

    return model_paths


def extract_table_from_model(model_class: type) -> Optional[ModelTable]:
    """
    Extract table information from a SQLAlchemy model class.

    Args:
        model_class: SQLAlchemy model class.

    Returns:
        ModelTable object or None if extraction fails.
    """
    try:
        table_name = model_class.__tablename__
        columns = []

        for column in model_class.__table__.columns:
            col = extract_column_info(column)
            if col:
                columns.append(col)

        table_options = _extract_table_options(model_class)

        return ModelTable(name=table_name, columns=columns, options=table_options)
    except Exception:
        return None


def _extract_table_options(model_class: type) -> dict:
    """Extract dialect-specific table options from SQLAlchemy model metadata."""

    options: dict = {}

    def _merge_option_dict(source: dict) -> None:
        info_values = source.get("info")
        for key, value in source.items():
            if key == "info":
                continue
            options[key] = value
        if isinstance(info_values, dict):
            for key, value in info_values.items():
                options[key] = value

    table_args = getattr(model_class, "__table_args__", None)

    if isinstance(table_args, dict):
        _merge_option_dict(dict(table_args))
    elif isinstance(table_args, tuple):
        for arg in table_args:
            if isinstance(arg, dict):
                _merge_option_dict(dict(arg))

    table_obj = getattr(model_class, "__table__", None)
    if table_obj is not None:
        table_info = getattr(table_obj, "info", None)
        if isinstance(table_info, dict):
            _merge_option_dict(dict(table_info))

    return options


def extract_column_info(column) -> Optional[ModelColumn]:
    """
    Extract column information from a SQLAlchemy column.

    Args:
        column: SQLAlchemy column object.

    Returns:
        ModelColumn object or None if extraction fails.
    """
    try:
        name = column.name
        type_str = str(column.type)
        nullable = column.nullable
        primary_key = column.primary_key
        unique = column.unique
        default = None
        if column.default:
            default_str = str(column.default)
            # SQLite doesn't support complex default expressions
            if default_str.startswith("ScalarElementColumnDefault"):
                # Extract the actual value from ScalarElementColumnDefault(True/False)
                import re

                match = re.search(r"ScalarElementColumnDefault\((.+)\)", default_str)
                if match:
                    value = match.group(1)
                    if value.lower() == "true":
                        default = "TRUE"
                    elif value.lower() == "false":
                        default = "FALSE"
                    elif value.isdigit():
                        default = value
                    else:
                        # Keep as-is for other simple values
                        default = value
            elif default_str.startswith("ColumnDefault"):
                # Handle ColumnDefault format
                import re

                match = re.search(r"ColumnDefault\((.+)\)", default_str)
                if match:
                    default = match.group(1)
            elif default_str.startswith("CallableColumnDefault"):
                # Handle CallableColumnDefault for Python callables like uuid4
                import re

                match = re.search(
                    r"CallableColumnDefault\(<function (\w+) at 0x[0-9a-f]+>\)",
                    default_str,
                )
                if match:
                    func_name = match.group(1)
                    # SQLite doesn't support Python callables as defaults
                    # For uuid4, we use a database-specific approach or omit
                    # Setting default to None so the column is created without a default
                    # The application must handle default value generation
                    default = None
                else:
                    # Try alternative pattern for callable defaults
                    match = re.search(r"CallableColumnDefault\((.+)\)", default_str)
                    if match:
                        default = None
            else:
                default = default_str

        foreign_key = None
        if column.foreign_keys:
            fk = list(column.foreign_keys)[0]
            colspec = fk._colspec
            # SQLite doesn't support table.column in REFERENCES, convert to format
            # SQLite expects: REFERENCES table(column) instead of table.column
            if "." in colspec:
                table, col = colspec.rsplit(".", 1)
                foreign_key = f"{table}({col})"
            else:
                foreign_key = colspec

        visit_name = getattr(column.type, "__visit_name__", None)
        column_info = dict(getattr(column, "info", {}) or {})

        return ModelColumn(
            name=name,
            type=type_str,
            nullable=nullable,
            primary_key=primary_key,
            unique=unique,
            default=default,
            foreign_key=foreign_key,
            visit_name=visit_name,
            info=column_info,
        )
    except Exception:
        return None


def compare_model_to_database(
    model_tables: List[ModelTable],
    db_tables: dict,
) -> List[SchemaDifference]:
    """
    Compare model definitions against database schema.

    Args:
        model_tables: List of tables from models.
        db_tables: Dictionary of tables from database inspection.

    Returns:
        List of SchemaDifference objects representing required changes.
    """
    differences = []

    model_table_names = {t.name for t in model_tables}
    db_table_names = set(db_tables.keys())

    new_tables = model_table_names - db_table_names
    dropped_tables = db_table_names - model_table_names

    for table_name in new_tables:
        for table in model_tables:
            if table.name == table_name:
                for col in table.columns:
                    differences.append(
                        SchemaDifference(
                            type="add_column",
                            table_name=table_name,
                            column_name=col.name,
                            sql=generate_add_column_sql(table_name, col),
                        )
                    )

    for table_name in dropped_tables:
        differences.append(
            SchemaDifference(
                type="drop_table",
                table_name=table_name,
                sql=f"DROP TABLE {table_name}",
            )
        )

    return differences


def generate_add_column_sql(table_name: str, column: ModelColumn) -> str:
    """Generate SQL for adding a column."""
    dialect_name = _get_active_dialect_name()

    if dialect_name == "clickhouse":
        column_sql = _render_clickhouse_column_definition(
            column, include_constraints=False
        )
        return f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"

    nullable_sql = "" if column.nullable else "NOT NULL"
    default_sql = f" DEFAULT {column.default}" if column.default else ""
    fk_sql = f" REFERENCES {column.foreign_key}" if column.foreign_key else ""

    return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column.type} {nullable_sql}{default_sql}{fk_sql}"


def generate_create_table_sql(table: ModelTable) -> str:
    """Generate CREATE TABLE SQL from a ModelTable."""
    dialect_name = _get_active_dialect_name()

    if dialect_name == "clickhouse":
        return _generate_clickhouse_create_table_sql(table)

    return _generate_default_create_table_sql(table)


def _generate_default_create_table_sql(table: ModelTable) -> str:
    """Default ANSI-style CREATE TABLE generator."""
    column_defs = []

    for col in table.columns:
        col_def = f"    {col.name} {col.type}"
        if not col.nullable:
            col_def += " NOT NULL"
        if col.primary_key:
            col_def += " PRIMARY KEY"
        elif col.unique:
            col_def += " UNIQUE"
        if col.default:
            col_def += f" DEFAULT {col.default}"
        if col.foreign_key:
            col_def += f" REFERENCES {col.foreign_key}"
        column_defs.append(col_def)

    columns_sql = ",\n".join(column_defs)

    return f"CREATE TABLE IF NOT EXISTS {table.name} (\n{columns_sql}\n)"


def _get_active_dialect_name() -> str:
    try:
        return get_current_dialect().name
    except Exception:
        return "sqlite"


CLICKHOUSE_TYPE_MAP = {
    "integer": "Int32",
    "bigint": "Int64",
    "smallint": "Int16",
    "tinyint": "Int8",
    "string": "String",
    "varchar": "String",
    "text": "String",
    "unicode_text": "String",
    "boolean": "UInt8",
    "datetime": "DateTime",
    "date": "Date",
    "float": "Float64",
    "float4": "Float32",
    "float8": "Float64",
    "numeric": "Decimal(18, 6)",
    "decimal": "Decimal(18, 6)",
    "uuid": "UUID",
}


def _render_clickhouse_column_definition(
    column: ModelColumn, include_constraints: bool = True
) -> str:
    custom_type = column.info.get("clickhouse_type")
    visit_name = (column.visit_name or column.type or "").lower()
    mapped_type = CLICKHOUSE_TYPE_MAP.get(visit_name, column.type)
    column_type = custom_type or mapped_type

    col_def = f"{column.name} {column_type}"
    if not column.nullable:
        col_def += " NOT NULL"
    if column.default:
        col_def += f" DEFAULT {column.default}"
    codec = column.info.get("clickhouse_codec")
    if codec:
        col_def += f" CODEC({codec})"

    if include_constraints:
        ttl = column.info.get("clickhouse_ttl")
        if ttl:
            col_def += f" TTL {ttl}"

    return col_def


def _generate_clickhouse_create_table_sql(table: ModelTable) -> str:
    columns_sql = ",\n".join(
        f"    {_render_clickhouse_column_definition(col)}" for col in table.columns
    )

    engine = table.options.get("clickhouse_engine", "MergeTree()")
    order_by = _normalize_clickhouse_clause(
        table.options.get("clickhouse_order_by"),
        default=_derive_order_by(table),
    )
    if not order_by:
        order_by = "tuple()"

    partition_by = _normalize_clickhouse_clause(
        table.options.get("clickhouse_partition_by"),
    )
    primary_key = _normalize_clickhouse_clause(
        table.options.get("clickhouse_primary_key"),
    )
    sample_by = _normalize_clickhouse_clause(table.options.get("clickhouse_sample_by"))
    ttl = table.options.get("clickhouse_ttl")
    settings = table.options.get("clickhouse_settings")

    clauses = [f"ENGINE = {engine}", f"ORDER BY {order_by}"]
    if partition_by:
        clauses.append(f"PARTITION BY {partition_by}")
    if primary_key:
        clauses.append(f"PRIMARY KEY {primary_key}")
    if sample_by:
        clauses.append(f"SAMPLE BY {sample_by}")
    if ttl:
        clauses.append(f"TTL {ttl}")

    settings_sql = _normalize_clickhouse_settings(settings)
    if settings_sql:
        clauses.append(f"SETTINGS {settings_sql}")

    clauses_sql = "\n".join(f"{clause}" for clause in clauses)

    return f"CREATE TABLE IF NOT EXISTS {table.name} (\n{columns_sql}\n)\n{clauses_sql}"


def _derive_order_by(table: ModelTable) -> str:
    pk_columns = [col.name for col in table.columns if col.primary_key]
    if pk_columns:
        return f"({', '.join(pk_columns)})"
    return "tuple()"


def _normalize_clickhouse_clause(value, default: Optional[str] = None) -> Optional[str]:
    if value is None:
        return default
    if isinstance(value, (list, tuple, set)):
        return f"({', '.join(str(v) for v in value)})"
    return str(value)


def _normalize_clickhouse_settings(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return str(value)


def generate_drop_table_sql(table_name: str) -> str:
    """Generate DROP TABLE SQL."""
    return f"DROP TABLE {table_name}"


def extract_tables_from_database(sqlalchemy_url: str) -> dict[str, set[str]]:
    """
    Extract table names and their columns from the actual database.

    Args:
        sqlalchemy_url: SQLAlchemy database URL.

    Returns:
        Dictionary mapping table names to sets of column names.
    """
    from sqlalchemy import create_engine, inspect

    tables: dict[str, set[str]] = {}

    try:
        engine = create_engine(sqlalchemy_url)
        inspector = inspect(engine)

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_names = {col["name"].lower() for col in columns}
            tables[table_name] = column_names

        engine.dispose()
    except Exception:
        pass

    return tables


def extract_tables_from_migrations(migrations_dir: str) -> dict[str, set[str]]:
    """
    Extract table names and their columns from existing migrations.

    Args:
        migrations_dir: Path to migrations directory.

    Returns:
        Dictionary mapping table names to sets of column names.
    """
    from dbwarden.engine.file_parser import parse_upgrade_statements

    tables: dict[str, set[str]] = {}

    if not os.path.exists(migrations_dir):
        return tables

    for filename in sorted(os.listdir(migrations_dir)):
        if not filename.endswith(".sql"):
            continue
        filepath = os.path.join(migrations_dir, filename)
        statements = parse_upgrade_statements(filepath)

        for stmt in statements:
            create_match = re.search(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(",
                stmt,
                re.IGNORECASE,
            )
            if create_match:
                table_name = create_match.group(1)

                columns_str_match = re.search(r"\((.+)\)", stmt, re.DOTALL)
                if columns_str_match:
                    columns_str = columns_str_match.group(1)
                    column_names = set()

                    column_parts = re.split(r",\s*(?![^()]*\))", columns_str)
                    for part in column_parts:
                        part = part.strip()
                        col_match = re.match(r"(\w+)", part, re.IGNORECASE)
                        if col_match:
                            col_name = col_match.group(1).lower()
                            if col_name not in (
                                "primary",
                                "foreign",
                                "unique",
                                "check",
                                "constraint",
                            ):
                                column_names.add(col_name)

                    if table_name in tables:
                        tables[table_name].update(column_names)
                    else:
                        tables[table_name] = column_names

    return tables
