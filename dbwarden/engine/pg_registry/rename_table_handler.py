from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
    TableRenameIntent,
    _get_backend,
    _rename_table_sql,
)


class RenameTableHandler(ObjectHandler):
    object_type: str = "rename_table"
    op_types: tuple[str, ...] = (
        "rename_table",
    )
    run_phase: RunPhase = RunPhase.DIFF
    statement_order: StatementOrder = StatementOrder.RENAME_TABLE

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {}

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        return {}

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        return spec

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        return [], []

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        intent = TableRenameIntent(
            old_table=op.upgrade_attrs["old_table"],
            new_table=op.upgrade_attrs["new_table"],
        )
        backend = _get_backend(db_name)
        return [_rename_table_sql(intent, backend)]
