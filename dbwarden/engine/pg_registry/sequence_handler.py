from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry.protocol import ObjectHandler, Op, RunPhase
from dbwarden.engine.snapshot import MigrationStatement, StatementOrder


class SequenceHandler(ObjectHandler):
    """Handler for PostgreSQL SEQUENCE objects.

    Sequences are declared in config (``pg_sequences``, ``RunPhase.PREAMBLE``).
    The snapshot currently has no ``sequences`` key, so ``extract`` returns
    empty — all model sequences are always treated as additions.

    The inline code at ``_build_sequence_sql`` / ``_drop_sequence_sql``
    provides the reference SQL generation.
    """

    object_type: str = "sequence"
    op_types: tuple[str, ...] = (
        "create_sequence",
        "drop_sequence",
    )
    run_phase: RunPhase = RunPhase.PREAMBLE
    statement_order: StatementOrder = StatementOrder.CREATE_SEQUENCE

    # ------------------------------------------------------------------
    # Extract — sequences not yet in snapshot
    # ------------------------------------------------------------------

    def extract(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Model spec — from config
    # ------------------------------------------------------------------

    def model_spec_from_config(self, config: Any) -> dict[str, Any]:
        raw: list[dict[str, Any]] = getattr(config, "pg_sequences", []) or []
        spec: dict[str, dict[str, Any]] = {}
        for entry in raw:
            name: str = entry["name"]
            info: dict[str, Any] = {}
            if entry.get("increment") is not None:
                info["increment"] = entry["increment"]
            if entry.get("minvalue") is not None:
                info["minvalue"] = entry["minvalue"]
            if entry.get("maxvalue") is not None:
                info["maxvalue"] = entry["maxvalue"]
            if entry.get("start") is not None:
                info["start"] = entry["start"]
            if entry.get("cycle"):
                info["cycle"] = True
            if entry.get("owned_by"):
                info["owned_by"] = entry["owned_by"]
            if entry.get("schema"):
                info["schema"] = entry["schema"]
            spec[name] = info
        return spec

    # ------------------------------------------------------------------
    # Model spec (DIFF path) — never from tables
    # ------------------------------------------------------------------

    def model_spec_from_tables(self, model_tables: list[Any]) -> dict[str, Any]:
        return {}

    # ------------------------------------------------------------------
    # Canonicalize
    # ------------------------------------------------------------------

    def canonicalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}
        result: dict[str, dict[str, Any]] = {}
        for key, val in spec.items():
            if val is None:
                continue
            name = key.lower()
            if isinstance(val, dict):
                entry: dict[str, Any] = {}
                for k in ("increment", "minvalue", "maxvalue", "start", "cycle", "owned_by", "schema"):
                    if k in val and val[k] is not None:
                        entry[k] = val[k]
                result[name] = entry
            else:
                result[name] = {}
        return result

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

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
            if name not in snap or snap.get(name) != info:
                upgrade_ops.append(
                    Op(
                        object_type="create_sequence",
                        upgrade_attrs={"seq_name": name, "seq_info": info},
                        rollback_attrs={"seq_name": name, "seq_info": info},
                    )
                )
                rollback_ops.append(
                    Op(
                        object_type="drop_sequence",
                        upgrade_attrs={"seq_name": name, "seq_info": info},
                        rollback_attrs={"seq_name": name, "seq_info": info},
                    )
                )

        for name in snap:
            if name not in model:
                snap_info = snap[name]
                upgrade_ops.append(
                    Op(
                        object_type="drop_sequence",
                        upgrade_attrs={"seq_name": name},
                        rollback_attrs={"seq_name": name, "seq_info": snap_info},
                    )
                )
                rollback_ops.append(
                    Op(
                        object_type="create_sequence",
                        upgrade_attrs={"seq_name": name, "seq_info": snap_info},
                        rollback_attrs={"seq_name": name, "seq_info": snap_info},
                    )
                )

        return upgrade_ops, rollback_ops

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------

    def emit(
        self, op: Op, db_name: Optional[str] = None
    ) -> List[MigrationStatement]:
        from dbwarden.engine.model_discovery import _qualified_name

        stmts: list[MigrationStatement] = []

        if op.object_type == "create_sequence":
            info = op.upgrade_attrs.get("seq_info", {})
            name = op.upgrade_attrs["seq_name"]
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            parts = [f"CREATE SEQUENCE IF NOT EXISTS {qname}"]
            if isinstance(info, dict):
                if info.get("increment") is not None:
                    parts.append(f"INCREMENT BY {info['increment']}")
                if info.get("minvalue") is not None:
                    parts.append(f"MINVALUE {info['minvalue']}")
                if info.get("maxvalue") is not None:
                    parts.append(f"MAXVALUE {info['maxvalue']}")
                if info.get("start") is not None:
                    parts.append(f"START WITH {info['start']}")
                if info.get("cycle"):
                    parts.append("CYCLE")
                else:
                    parts.append("NO CYCLE")
                if info.get("owned_by"):
                    parts.append(f"OWNED BY {info['owned_by']}")
            up = " ".join(parts) + ";"
            rb = f"DROP SEQUENCE IF EXISTS {qname};"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_SEQUENCE,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        elif op.object_type == "drop_sequence":
            name = op.upgrade_attrs["seq_name"]
            info = op.upgrade_attrs.get("seq_info")
            schema = info.get("schema") if isinstance(info, dict) else None
            qname = _qualified_name(name, schema)
            up = f"DROP SEQUENCE IF EXISTS {qname};"
            if isinstance(info, dict):
                parts = [f"CREATE SEQUENCE IF NOT EXISTS {qname}"]
                if info.get("increment") is not None:
                    parts.append(f"INCREMENT BY {info['increment']}")
                if info.get("minvalue") is not None:
                    parts.append(f"MINVALUE {info['minvalue']}")
                if info.get("maxvalue") is not None:
                    parts.append(f"MAXVALUE {info['maxvalue']}")
                if info.get("start") is not None:
                    parts.append(f"START WITH {info['start']}")
                if info.get("cycle"):
                    parts.append("CYCLE")
                else:
                    parts.append("NO CYCLE")
                if info.get("owned_by"):
                    parts.append(f"OWNED BY {info['owned_by']}")
                rb = " ".join(parts) + ";"
            else:
                rb = f"-- Revert: CREATE SEQUENCE {qname};"
            stmts.append(
                MigrationStatement(
                    order=StatementOrder.CREATE_SEQUENCE,
                    upgrade_sql=up,
                    rollback_sql=rb,
                )
            )

        return stmts
