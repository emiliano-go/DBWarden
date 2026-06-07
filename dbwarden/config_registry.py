from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from dbwarden.config_schema import DatabaseEntry, DatabaseType, structure_database_entry

if TYPE_CHECKING:
    from dbwarden.db_handle import DatabaseHandle


@dataclass
class _Registry:
    _entries: list[DatabaseEntry]
    _reset_hooks: list[Callable[[], None]]

    def add(self, entry: DatabaseEntry) -> None:
        self._entries.append(entry)

    def entries(self) -> list[DatabaseEntry]:
        return list(self._entries)

    def reset(self) -> None:
        self._entries = []
        for hook in self._reset_hooks:
            hook()

    def register_reset_hook(self, hook: Callable[[], None]) -> None:
        self._reset_hooks.append(hook)


_REGISTRY = _Registry(_entries=[], _reset_hooks=[])


def register_reset_hook(hook: Callable[[], None]) -> None:
    _REGISTRY.register_reset_hook(hook)


def reset_registry() -> None:
    _REGISTRY.reset()


def registered_entries() -> list[DatabaseEntry]:
    return _REGISTRY.entries()


def database_config(
    *,
    database_name: str,
    database_type: DatabaseType = "sqlite",
    database_url_sync: str | None = None,
    database_url_async: str | None = None,
    secure_values: bool = False,
    default: bool = False,
    migrations_dir: str | None = None,
    migration_table: str | None = None,
    model_paths: list[str] | None = None,
    dev_database_type: DatabaseType | None = None,
    dev_database_url: str | None = None,
    overlap_models: bool = False,
    seed_table: str | None = None,
) -> DatabaseHandle:
    from dbwarden.db_handle import DatabaseHandle as _DH

    entry = structure_database_entry(
        dict(
            database_name=database_name,
            database_type=database_type,
            database_url_sync=database_url_sync,
            database_url_async=database_url_async,
            secure_values=secure_values,
            default=default,
            migrations_dir=migrations_dir,
            migration_table=migration_table,
            model_paths=model_paths,
            dev_database_type=dev_database_type,
            dev_database_url=dev_database_url,
            overlap_models=overlap_models,
            seed_table=seed_table,
        )
    )
    _REGISTRY.add(entry)
    return _DH(entry.database_name, entry.database_type)
