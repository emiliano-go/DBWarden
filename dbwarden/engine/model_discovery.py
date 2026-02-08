import os
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
    ):
        self.name = name
        self.type = type
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.default = default
        self.foreign_key = foreign_key

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "unique": self.unique,
            "default": self.default,
            "foreign_key": self.foreign_key,
        }


class ModelTable:
    """Represents a table from a SQLAlchemy model."""

    def __init__(
        self,
        name: str,
        columns: List[ModelColumn],
    ):
        self.name = name
        self.columns = columns

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": [col.to_dict() for col in self.columns],
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
        ".env",
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

        return ModelTable(name=table_name, columns=columns)
    except Exception:
        return None


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

        return ModelColumn(
            name=name,
            type=type_str,
            nullable=nullable,
            primary_key=primary_key,
            unique=unique,
            default=default,
            foreign_key=foreign_key,
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
    nullable_sql = "" if column.nullable else "NOT NULL"
    default_sql = f" DEFAULT {column.default}" if column.default else ""
    fk_sql = f" REFERENCES {column.foreign_key}" if column.foreign_key else ""

    return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column.type} {nullable_sql}{default_sql}{fk_sql}"


def generate_create_table_sql(table: ModelTable) -> str:
    """Generate CREATE TABLE SQL from a ModelTable."""
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


def generate_drop_table_sql(table_name: str) -> str:
    """Generate DROP TABLE SQL."""
    return f"DROP TABLE {table_name}"
