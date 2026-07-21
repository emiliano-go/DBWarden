from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.backends.clickhouse.cluster import emit_with_cluster
from dbwarden.engine.backends.clickhouse.secrets import _REDACTED, strip_secret_values
from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder

_SECRET_KEYS: frozenset[str] = frozenset()


def _named_collection_parts(entries: dict[str, Any], overridable: Any = None) -> list[str]:
    parts = [f"{k} = '{v}'" for k, v in entries.items()]
    if isinstance(overridable, dict):
        for k, v in overridable.items():
            if v is False:
                parts.append(f"{k} NOT OVERRIDABLE")
    return parts or ["_ = ''"]


def _create_named_collection_stmt(name: str, entries: dict[str, Any], overridable: Any = None):
    from dbwarden.engine.backends.clickhouse.cluster import ClusterableStatement

    return ClusterableStatement(
        prefix=f"CREATE NAMED COLLECTION {name}",
        suffix=f"AS {', '.join(_named_collection_parts(entries, overridable))}",
    )


def _drop_named_collection_stmt(name: str):
    from dbwarden.engine.backends.clickhouse.cluster import ClusterableStatement

    return ClusterableStatement(prefix=f"DROP NAMED COLLECTION {name}", suffix="")


class ChNamedCollectionHandler(ObjectHandler):
    object_type: str = "ch_named_collection"
    op_types: tuple[str, ...] = (
        "create_ch_named_collection",
        "drop_ch_named_collection",
        "alter_ch_named_collection",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_EXTENSION

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        raw = snapshot.get("named_collections", {})
        result: dict[str, dict[str, Any]] = {}
        for name, collection in raw.items():
            entries = dict(collection.get("entries", {}))
            entries = strip_secret_values(entries, _SECRET_KEYS)
            result[name] = {
                "name": name,
                "entries": entries,
                "overridable": collection.get("overridable"),
            }
        return result

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[Any] = getattr(config, "ch_named_collections", []) or []
        result: dict[str, dict[str, Any]] = {}
        for entry in raw:
            if hasattr(entry, "to_dict"):
                d = entry.to_dict()
            else:
                d = dict(entry)
            name = d.get("name", "")
            entries = dict(d.get("entries", {}))
            overridable = d.get("overridable")
            result[name] = {"name": name, "entries": entries, "overridable": overridable}
        return result

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for name, val in spec.items():
            if val is None:
                continue
            entries = dict(val.get("entries", {}))
            for k in list(entries.keys()):
                if entries[k] is None:
                    entries.pop(k)
            result[name] = {
                "name": name,
                "entries": entries,
                "overridable": val.get("overridable"),
            }
        return result

    def diff(
        self,
        snap_spec: dict[str, Any],
        model_spec: dict[str, Any],
    ) -> Tuple[List[Op], List[Op]]:
        upgrade_ops: list[Op] = []
        rollback_ops: list[Op] = []

        snap = snap_spec or {}
        model = model_spec or {}

        for name, info in model.items():
            if name not in snap:
                upgrade_ops.append(Op(
                    object_type="create_ch_named_collection",
                    upgrade_attrs={"name": name, "entries": info.get("entries", {}), "overridable": info.get("overridable")},
                    rollback_attrs={"name": name},
                ))
                rollback_ops.insert(0, Op(
                    object_type="drop_ch_named_collection",
                    upgrade_attrs={"name": name},
                    rollback_attrs={"name": name, "entries": info.get("entries", {}), "overridable": info.get("overridable")},
                ))
            else:
                snap_info = snap[name]
                snap_entries = snap_info.get("entries", {})
                model_entries = info.get("entries", {})
                snap_overridable = snap_info.get("overridable")
                model_overridable = info.get("overridable")
                if snap_entries != model_entries or snap_overridable != model_overridable:
                    upgrade_ops.append(Op(
                        object_type="alter_ch_named_collection",
                        upgrade_attrs={"name": name, "entries": model_entries, "overridable": model_overridable},
                        rollback_attrs={"name": name, "entries": snap_entries, "overridable": snap_overridable},
                    ))
                    rollback_ops.insert(0, Op(
                        object_type="alter_ch_named_collection",
                        upgrade_attrs={"name": name, "entries": snap_entries, "overridable": snap_overridable},
                        rollback_attrs={"name": name, "entries": model_entries, "overridable": model_overridable},
                    ))

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                rollback_ops.insert(0, Op(
                    object_type="create_ch_named_collection",
                    upgrade_attrs={"name": name, "entries": snap_info.get("entries", {}), "overridable": snap_info.get("overridable")},
                    rollback_attrs={"name": name},
                ))
                upgrade_ops.append(Op(
                    object_type="drop_ch_named_collection",
                    upgrade_attrs={"name": name},
                    rollback_attrs={"name": name, "entries": snap_info.get("entries", {}), "overridable": snap_info.get("overridable")},
                ))

        return upgrade_ops, rollback_ops

    @emit_with_cluster
    def emit(
        self, op: Op, db_name: Optional[str] = None,
        **kwargs: Any,
    ) -> List[MigrationStatement]:
        from dbwarden.engine.backends.clickhouse.cluster import ClusterableStatement

        name = op.upgrade_attrs["name"]
        stmts: list[MigrationStatement] = []

        if op.object_type == "create_ch_named_collection":
            entries = op.upgrade_attrs.get("entries", {})
            overridable = op.upgrade_attrs.get("overridable")
            up = _create_named_collection_stmt(name, entries, overridable)
            rb = _drop_named_collection_stmt(name)
            stmts.append(up.to_migration(self.statement_order, self._cluster_ctx, rollback=rb))

        elif op.object_type == "drop_ch_named_collection":
            up = _drop_named_collection_stmt(name)
            rb_entries = op.rollback_attrs.get("entries")
            if isinstance(rb_entries, dict):
                rb = _create_named_collection_stmt(
                    name,
                    rb_entries,
                    op.rollback_attrs.get("overridable"),
                )
                stmts.append(up.to_migration(self.statement_order, self._cluster_ctx, rollback=rb))
            else:
                stmts.append(MigrationStatement(
                    order=self.statement_order,
                    upgrade_sql=up.render(self._cluster_ctx),
                    rollback_sql=f"-- Revert: CREATE NAMED COLLECTION {name};",
                    rollback_kind="placeholder",
                    rollback_reason="previous named collection entries were not captured",
                ))

        elif op.object_type == "alter_ch_named_collection":
            entries = op.upgrade_attrs.get("entries", {})
            overridable = op.upgrade_attrs.get("overridable")
            snap_entries = op.rollback_attrs.get("entries", {})
            snap_overridable = op.rollback_attrs.get("overridable")
            up_sql = "\n".join([
                _drop_named_collection_stmt(name).render(self._cluster_ctx) + ";",
                _create_named_collection_stmt(name, entries, overridable).render(self._cluster_ctx) + ";",
            ])
            rb_sql = "\n".join([
                _drop_named_collection_stmt(name).render(self._cluster_ctx) + ";",
                _create_named_collection_stmt(name, snap_entries, snap_overridable).render(self._cluster_ctx) + ";",
            ])
            stmts.append(MigrationStatement(
                order=self.statement_order,
                upgrade_sql=up_sql,
                rollback_sql=rb_sql,
            ))

        return stmts
