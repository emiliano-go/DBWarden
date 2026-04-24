from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from dbwarden.config_schema import DatabaseEntry, structure_database_entry


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


def database_config(**kwargs) -> None:
    entry = structure_database_entry(kwargs)
    _REGISTRY.add(entry)
