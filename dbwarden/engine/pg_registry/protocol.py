from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, List, Optional, Protocol, Tuple

from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class RunPhase(IntEnum):
    PREAMBLE = 0
    DIFF = 1


@dataclass
class Op:
    object_type: str
    upgrade_attrs: dict[str, Any] = field(default_factory=dict)
    rollback_attrs: dict[str, Any] = field(default_factory=dict)
    irreversible: bool = False


class ObjectHandler(Protocol):
    object_type: str
    run_phase: RunPhase
    statement_order: StatementOrder

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        ...

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        ...

    def model_spec_from_tables(
        self, model_tables: list[Any]
    ) -> dict[str, Any]:
        ...

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        ...

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        ...

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        ...
