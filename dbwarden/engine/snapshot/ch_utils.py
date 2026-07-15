from __future__ import annotations

import json
from typing import Any


_CH_COLUMN_KEYS: frozenset[str] = frozenset({
    "ch_codec",
    "ch_default_expression",
    "ch_materialized",
    "ch_alias",
    "ch_ttl",
    "ch_low_cardinality",
    "ch_nullable",
    "ch_type",
})


def _clean_clickhouse_expression(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip('\x00').strip()
    return s if s else None


def _serialize_clickhouse_engine(engine: Any) -> str | tuple | None:
    if engine is None:
        return None
    if isinstance(engine, dict):
        name = engine.get("name")
        if not name:
            return None
        args = list(engine.get("args", []) or [])
        if engine.get("zookeeper_path") is not None:
            args.insert(0, engine["zookeeper_path"])
        if engine.get("replica_name") is not None:
            args.insert(1 if engine.get("zookeeper_path") is not None else 0, engine["replica_name"])
        if not args:
            return name
        return tuple([name] + args)
    if hasattr(engine, "name"):
        args = [engine.name]
        if getattr(engine, "zookeeper_path", None) is not None:
            args.append(engine.zookeeper_path)
        if getattr(engine, "replica_name", None) is not None:
            args.append(engine.replica_name)
        args.extend(list(getattr(engine, "args", ()) or ()))
        return args[0] if len(args) == 1 else tuple(args)
    return engine


def _pick_clickhouse_codec(codec_expr: Any) -> str | None:
    if codec_expr is None:
        return None
    codec = str(codec_expr).strip()
    if not codec:
        return None
    parts = [part.strip() for part in codec.split(",") if part.strip()]
    if not parts:
        return None
    non_default = [part for part in parts if not part.upper().startswith("LZ4")]
    return non_default[-1] if non_default else parts[-1]


def _check_ch_engine_recreate_allowed(snap_spec: dict, model_spec: dict, table_name: str) -> None:
    reasons: list[str] = []
    for spec, label in [(snap_spec, "current"), (model_spec, "new")]:
        if spec.get("ch_object_type") == "materialized_view" and spec.get("ch_to_table"):
            reasons.append(f"is a materialized view with 'TO {spec['ch_to_table']}' ({label})")
        elif spec.get("ch_select_statement") and spec.get("ch_to_table"):
            reasons.append(f"has a SELECT statement and 'TO' target ({label})")
    if reasons:
        raise ValueError(
            f"ClickHouse table '{table_name}' cannot be automatically recreated: "
            f"{'; '.join(reasons)}. "
            "Handle manually or use --force to skip this check."
        )


def _diff_ch_column_extras(
    snap_ch_col: dict,
    model_ch_col: dict,
    table_name: str,
    col_name: str,
    upgrade_ops: list[dict],
    rollback_ops: list[dict],
) -> None:
    if json.dumps(snap_ch_col, sort_keys=True, default=str) != json.dumps(model_ch_col, sort_keys=True, default=str):
        upgrade_ops.append({
            "type": "alter_ch_column",
            "table": table_name,
            "column": col_name,
            "from_ch_column": snap_ch_col,
            "to_ch_column": model_ch_col,
        })
        rollback_ops.append({
            "type": "alter_ch_column",
            "table": table_name,
            "column": col_name,
            "from_ch_column": model_ch_col,
            "to_ch_column": snap_ch_col,
        })
