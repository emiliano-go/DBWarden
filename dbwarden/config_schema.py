from __future__ import annotations

from typing import Literal
import re

import cattrs
from attrs import define, field, validators
from cattrs import transform_error

from dbwarden.exceptions import ConfigurationError

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]
VALID_DATABASE_TYPES = frozenset(
    {"sqlite", "postgresql", "mysql", "mariadb", "clickhouse"}
)

DATABASE_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
MODEL_PATH_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_/]*$")
MAX_PATH_LENGTH = 200
MAX_PATH_COUNT = 10


def _validate_database_name(_self, _attribute, value: str) -> None:
    if not value or not DATABASE_NAME_RE.match(value):
        raise ValueError(
            "Invalid database_name. Must start with letter, contain only "
            "alphanumeric and underscores."
        )


def _validate_model_paths_for_list(value: list[str]) -> None:
    """Validate model_paths when it's a non-empty list."""
    if not isinstance(value, list):
        raise ValueError("model_paths must be a list")
    if len(value) > MAX_PATH_COUNT:
        raise ValueError(f"Too many model_paths: max {MAX_PATH_COUNT}")
    for path in value:
        if not isinstance(path, str):
            raise ValueError("model_paths must contain strings")
        if len(path) > MAX_PATH_LENGTH:
            raise ValueError(
                f"model_path too long: max {MAX_PATH_LENGTH} chars"
            )
        if ".." in path or path.startswith("/"):
            raise ValueError(
                f"Invalid model_path '{path}': no absolute paths or traversal"
            )
        if not MODEL_PATH_RE.match(path):
            raise ValueError(
                f"Invalid model_path '{path}': must be relative, alphanumeric/underscore"
            )


def _validate_database_type(_self, _attribute, value: str) -> None:
    if value not in VALID_DATABASE_TYPES:
        allowed = ", ".join(sorted(VALID_DATABASE_TYPES))
        raise ValueError(
            f"Invalid database_type '{value}'. Must be one of: {allowed}"
        )


@define(slots=False)
class DatabaseEntry:
    database_name: str = field(validator=_validate_database_name)
    database_type: DatabaseType = field(validator=_validate_database_type)
    database_url: str = field(validator=validators.min_len(1))
    secure_values: bool = False
    default: bool = False
    migrations_dir: str | None = None
    model_paths: list[str] | None = None
    dev_database_type: DatabaseType | None = None
    dev_database_url: str | None = None
    overlap_models: bool = False


@define(slots=False)
class MultiDatabaseConfig:
    default: str
    databases: dict[str, DatabaseEntry]


_CONVERTER = cattrs.Converter(detailed_validation=True)


def structure_database_entry(kwargs: dict) -> DatabaseEntry:
    try:
        return _CONVERTER.structure(kwargs, DatabaseEntry)
    except Exception as exc:
        messages = transform_error(exc)
        joined = "; ".join(messages) if messages else str(exc)
        raise ConfigurationError(joined) from exc
