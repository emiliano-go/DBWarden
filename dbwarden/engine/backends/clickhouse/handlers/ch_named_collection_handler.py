from __future__ import annotations

from typing import Any, List, Optional, Tuple

from dbwarden.engine.backends.clickhouse.cluster import emit_with_cluster
from dbwarden.engine.backends.clickhouse.secrets import _REDACTED, strip_secret_values
from dbwarden.engine.core.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder

_SECRET_KEYS: frozenset[str] = frozenset()


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
            parts = [f"{k} = '{v}'" for k, v in entries.items()]
            if overridable:
                for k, v in overridable.items():
                    if v is False:
                        parts.append(f"{k} NOT OVERRIDABLE")
            up = ClusterableStatement(
                prefix=f"CREATE NAMED COLLECTION {name}",
                suffix=f"AS {', '.join(parts)}" if parts else f"AS _ = ''",
            )
            rb = ClusterableStatement(
                prefix=f"DROP NAMED COLLECTION {name}",
                suffix="",
            )
            stmts.append(up.to_migration(self.statement_order, self._cluster_ctx, rollback=rb))

        elif op.object_type == "drop_ch_named_collection":
            up = ClusterableStatement(
                prefix=f"DROP NAMED COLLECTION {name}",
                suffix="",
            )
            stmts.append(up.to_migration(self.statement_order, self._cluster_ctx))

        elif op.object_type == "alter_ch_named_collection":
            entries = op.upgrade_attrs.get("entries", {})
            overridable = op.upgrade_attrs.get("overridable")
            snap_entries = op.rollback_attrs.get("entries", {})
            snap_overridable = op.rollback_attrs.get("overridable")

            set_parts = [f"SET {k} = '{v}'" for k, v in entries.items() if k not in snap_entries or snap_entries[k] != v]
            delete_keys = [k for k in snap_entries if k not in entries]
            if delete_keys:
                set_parts.append(f"DELETE {', '.join(delete_keys)}")
            rb_set_parts = [f"SET {k} = '{v}'" for k, v in snap_entries.items() if k not in entries or entries[k] != v]
            rb_delete_keys = [k for k in entries if k not in snap_entries]
            if rb_delete_keys:
                rb_set_parts.append(f"DELETE {', '.join(rb_delete_keys)}")

            up_suffix = "; ".join(set_parts) if set_parts else "-- no-op"
            rb_suffix = "; ".join(rb_set_parts) if rb_set_parts else "-- no-op"

            up = ClusterableStatement(
                prefix=f"ALTER NAMED COLLECTION {name}",
                suffix=up_suffix,
            )
            rb = ClusterableStatement(
                prefix=f"ALTER NAMED COLLECTION {name}",
                suffix=rb_suffix,
            )
            stmts.append(up.to_migration(self.statement_order, self._cluster_ctx, rollback=rb))

        return stmts
