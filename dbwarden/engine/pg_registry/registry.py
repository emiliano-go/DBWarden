from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, _assemble_migration


class RegistryDriver:
    """Orchestrates all registered ObjectHandlers to produce ops and SQL.

    Phase 0: zero-handler fallthrough wraps the existing inline logic.
    As handlers are registered (enum → domain → sequence → …) each
    handler's lifecycle replaces the corresponding inline code path.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, ObjectHandler] = {}

    def register(self, handler: ObjectHandler) -> None:
        self._handlers[handler.object_type] = handler

    def run(
        self,
        snapshot: dict[str, Any],
        model_tables: list[Any],
        config: Any,
    ) -> Tuple[List[Op], List[Op]]:
        all_upgrade: list[Op] = []
        all_rollback: list[Op] = []

        for handler in self._handlers.values():
            snap_spec = handler.extract(snapshot)
            snap_canonical = handler.canonicalize(snap_spec)

            if handler.run_phase == RunPhase.PREAMBLE:
                model_spec = handler.model_spec_from_config(config)
            else:
                model_spec = handler.model_spec_from_tables(model_tables)

            model_canonical = handler.canonicalize(model_spec)

            up, rb = handler.diff(snap_canonical, model_canonical)
            all_upgrade.extend(up)
            all_rollback.extend(rb)

        return all_upgrade, all_rollback

    def emit_all(
        self,
        ops: List[Op],
        db_name: Optional[str] = None,
    ) -> List[MigrationStatement]:
        stmts: list[MigrationStatement] = []
        ops_by_type: dict[str, list[Op]] = {}
        for op in ops:
            ops_by_type.setdefault(op.object_type, []).append(op)
        for handler in self._handlers.values():
            handler_op_types = getattr(handler, "op_types", (handler.object_type,))
            for ot in handler_op_types:
                for op in ops_by_type.get(ot, []):
                    stmts.extend(handler.emit(op, db_name=db_name))
        return stmts

    def emit_op_to_sql(
        self,
        upgrade_ops: List[Op],
        rollback_ops: List[Op],
        db_name: Optional[str] = None,
    ) -> Tuple[str, str, List[Change]]:
        all_stmts = (
            self.emit_all(upgrade_ops, db_name=db_name)
            + self.emit_all(rollback_ops, db_name=db_name)
        )
        up_sql, rb_sql = _assemble_migration(all_stmts)
        changes: list[Change] = []
        return up_sql, rb_sql, changes
