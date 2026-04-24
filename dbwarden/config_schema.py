from __future__ import annotations

from typing import Literal

import cattrs
from attrs import define, field, validators
from cattrs import transform_error

from dbwarden.exceptions import ConfigurationError

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]
VALID_DATABASE_TYPES = frozenset(
    {"sqlite", "postgresql", "mysql", "mariadb", "clickhouse"}
)


def _validate_database_type(_self, _attribute, value: str) -> None:
    if value not in VALID_DATABASE_TYPES:
        allowed = ", ".join(sorted(VALID_DATABASE_TYPES))
        raise ValueError(
            f"Invalid database_type '{value}'. Must be one of: {allowed}"
        )


@define(slots=False)
class DatabaseEntry:
    database_name: str = field(validator=validators.min_len(1))
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
