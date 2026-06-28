from __future__ import annotations

import json
import re
from dataclasses import asdict
from enum import Enum
from typing import Any

from sqlalchemy import text

from dbwarden.database.connection import get_db_connection
from dbwarden.engine.model_discovery import (
    ModelTable,
    get_all_model_tables,
    filter_model_tables_by_name,
    validate_model_tables_exist,
)
from dbwarden.models import SafetyIssue


class Safety(str, Enum):
    SAFE = "SAFE"
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


def classify_pg_type_change(from_type: dict[str, Any], to_type: dict[str, Any]) -> str:
    from_kind = from_type.get("kind") or from_type.get("type")
    to_kind = to_type.get("kind") or to_type.get("type")

    if from_kind == "varchar" and to_kind == "varchar":
        fl, tl = from_type.get("length"), to_type.get("length")
        if fl is None or tl is None or tl >= fl:
            return "SAFE"
        return "CRITICAL"
    if from_kind == "integer" and to_kind == "biginteger":
        return "SAFE"
    if from_kind == "varchar" and to_kind == "text":
        return "SAFE"
    if from_kind == "json" and to_kind == "jsonb":
        return "SAFE"
    if {from_kind, to_kind} == {"timestamp", "timestamptz"}:
        return "WARN"
    if from_kind == "numeric":
        fp = from_type.get("precision")
        tp = to_type.get("precision")
        if fp and tp and tp < fp:
            return "CRITICAL"
    if from_kind != to_kind:
        return "CRITICAL"
    return "SAFE"


def classify_enum_change(from_values: list[str], to_values: list[str]) -> str:
    if set(from_values) - set(to_values):
        return "CRITICAL"
    if set(to_values) - set(from_values):
        return "WARN"
    return "SAFE"


def _normalize_option_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def _snapshot_column_type_signature(snapshot_column: dict[str, Any]) -> dict[str, Any]:
    extra_keys = {"length", "precision", "scale", "pg_type", "enum_name"}
    if not any(key in snapshot_column for key in extra_keys):
        from dbwarden.engine.snapshot import normalize_type

        return normalize_type(str(snapshot_column.get("type", "")))

    sig: dict[str, Any] = {"type": snapshot_column.get("type")}
    for key in ("length", "precision", "scale", "pg_type", "enum_name"):
        if key in snapshot_column:
            sig[key] = snapshot_column[key]
    return sig


def extract_schema_snapshot(database: str | None = None) -> dict[str, dict[str, Any]]:
    from dbwarden.config import get_database
    from dbwarden.engine.snapshot import extract_full_schema_snapshot

    config = get_database(database)
    full = extract_full_schema_snapshot(database=database)
    if config.database_type == "clickhouse":
        snapshot: dict[str, dict[str, Any]] = {}
        for table_name, table in full.get("tables", {}).items():
            ch_opts = table.get("ch_options", {})
            clickhouse_options: dict[str, Any] = {}
            for ch_key, value in ch_opts.items():
                ck = _CH_OPTION_KEY_MAP.get(ch_key, ch_key)
                if value is not None:
                    clickhouse_options[ck] = value
            snapshot[table_name] = {
                "database_type": "clickhouse",
                "object_type": table.get("object_type", "table"),
                "comment": table.get("comment"),
                "columns": table.get("columns", {}),
                "clickhouse_options": clickhouse_options,
            }
        return snapshot
    if config.database_type == "postgresql":
        snapshot: dict[str, dict[str, Any]] = {}
        for table_name, table in full.get("tables", {}).items():
            snapshot[table_name] = {
                "database_type": "postgresql",
                "object_type": "table",
                "comment": table.get("comment"),
                "columns": table.get("columns", {}),
                "pg_table": table.get("pg_table", {}),
                "clickhouse_options": {},
            }
        return snapshot
    return _extract_generic_schema_snapshot(database)


def _extract_generic_schema_snapshot(database: str | None = None) -> dict[str, dict[str, Any]]:
    from sqlalchemy import inspect

    snapshot: dict[str, dict[str, Any]] = {}
    with get_db_connection(database) as connection:
        inspector = inspect(connection)
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            snapshot[table_name] = {
                "object_type": "table",
                "columns": {
                    col["name"]: {
                        "type": str(col["type"]),
                        "nullable": bool(col.get("nullable", True)),
                        "default": col.get("default"),
                    }
                    for col in columns
                },
                "clickhouse_options": {},
            }
    return snapshot


def _clean_expression(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    if not value_str:
        return None
    return value_str


def _parse_tuple_expression(value: Any) -> str | list[str] | None:
    value_str = _clean_expression(value)
    if value_str is None:
        return None
    if value_str.startswith("tuple(") and value_str.endswith(")"):
        inner = value_str[6:-1].strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",")]
    # Handle bare comma-separated list (common in ClickHouse 24.x)
    if "," in value_str:
        parts = [part.strip() for part in value_str.split(",")]
        if len(parts) > 1:
            return parts
    return value_str


def _parse_ttl_expressions(create_query: str) -> list[str]:
    ttl_match = re.search(
        r"\bTTL\s+(.+?)(?:\s+(?:SETTINGS|COMMENT|AS|PRIMARY KEY|ORDER BY|PARTITION BY|SAMPLE BY)\b|$)",
        create_query,
        re.IGNORECASE,
    )
    if not ttl_match:
        return []
    ttl_body = ttl_match.group(1).strip()
    return [part.strip() for part in ttl_body.split(",") if part.strip()]


def _parse_projection_queries(create_query: str) -> list[dict[str, str]]:
    from dbwarden.engine.snapshot import _extract_balanced_parens
    results: list[dict[str, str]] = []
    pattern = re.compile(r"PROJECTION\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.IGNORECASE)
    pos = 0
    while True:
        match = pattern.search(create_query, pos)
        if not match:
            break
        name = match.group(1)
        query = _extract_balanced_parens(match)
        results.append({"name": name, "query": (query or "").strip()})
        pos = match.end()
    return results


def _parse_projection_names(create_query: str) -> list[str]:
    return [p["name"] for p in _parse_projection_queries(create_query)]


def _parse_mv_query(create_query: str) -> str | None:
    mv_match = re.search(r"\bAS\s+SELECT\s+.+$", create_query, re.IGNORECASE | re.DOTALL)
    if not mv_match:
        return None
    return mv_match.group(0)[3:].strip()


def _parse_zookeeper_path(create_query: str, engine: str) -> str | None:
    if "Replicated" not in engine:
        return None
    match = re.search(r"\bReplicated\w+\s*\(([^,]+),", create_query)
    if match:
        return match.group(1).strip()
    return None


def _parse_replica_name(create_query: str, engine: str) -> str | None:
    if "Replicated" not in engine:
        return None
    match = re.search(r"\bReplicated\w+\s*\([^,]+,\s*([^)]+)", create_query)
    if match:
        return match.group(1).strip()
    return None


def analyze_schema(
    model_tables: list[ModelTable],
    schema_snapshot: dict[str, dict[str, Any]],
) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    model_by_name = {table.name: table for table in model_tables}
    snapshot_names = set(schema_snapshot.keys())
    model_names = set(model_by_name.keys())

    for table_name in sorted(model_names - snapshot_names):
        table = model_by_name[table_name]
        object_label = table.object_type.replace("_", " ")
        issues.append(
            SafetyIssue(
                severity="INFO",
                change_type="create_table",
                table_name=table_name,
                message=f"Create {object_label} '{table_name}'",
            )
        )

    for table_name in sorted(snapshot_names - model_names):
        issues.append(
            SafetyIssue(
                severity="WARNING",
                change_type="drop_table",
                table_name=table_name,
                message=f"Drop table '{table_name}'",
                required_flag="--force",
            )
        )

    for table_name in sorted(snapshot_names & model_names):
        model_table = model_by_name[table_name]
        table_snapshot = schema_snapshot[table_name]
        issues.extend(_analyze_table(table_snapshot, model_table))

    return issues


def _analyze_table(table_snapshot: dict[str, Any], model_table: ModelTable) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    snapshot_columns = table_snapshot.get("columns", {})
    model_columns = {column.name: column for column in model_table.columns}

    if table_snapshot.get("comment") != model_table.comment:
        issues.append(
            SafetyIssue(
                severity="INFO",
                change_type="change_table_comment",
                table_name=model_table.name,
                message=f"Change comment of table '{model_table.name}'",
            )
        )

    if table_snapshot.get("object_type", "table") != model_table.object_type:
        issues.append(
            SafetyIssue(
                severity="WARNING",
                change_type="change_object_type",
                table_name=model_table.name,
                message=(
                    f"Change object type for '{model_table.name}' from "
                    f"{table_snapshot.get('object_type', 'table')} to {model_table.object_type}"
                ),
                required_flag="--force",
            )
        )

    for column_name in sorted(model_columns.keys() - snapshot_columns.keys()):
        column = model_columns[column_name]
        issues.append(
            SafetyIssue(
                severity="INFO",
                change_type="add_column",
                table_name=model_table.name,
                column_name=column_name,
                message=f"Add column '{column_name}' to '{model_table.name}'",
            )
        )

    for column_name in sorted(snapshot_columns.keys() - model_columns.keys()):
        issues.append(
            SafetyIssue(
                severity="WARNING",
                change_type="drop_column",
                table_name=model_table.name,
                column_name=column_name,
                message=f"Drop column '{column_name}' from '{model_table.name}'",
                required_flag="--force",
            )
        )

    for column_name in sorted(snapshot_columns.keys() & model_columns.keys()):
        snapshot_column = snapshot_columns[column_name]
        model_column = model_columns[column_name]
        from dbwarden.engine.snapshot import normalize_type, _model_type_str

        snapshot_type = _snapshot_column_type_signature(snapshot_column)
        model_type = normalize_type(_model_type_str(model_column.type))
        model_pg_column = None
        if model_column.pg_meta:
            model_pg_column = {}
            for src, dst in (
                ("pg_collation", "collation"),
                ("pg_storage", "storage"),
                ("pg_compression", "compression"),
                ("pg_generated", "generated"),
                ("pg_identity", "identity"),
                ("pg_identity_start", "identity_start"),
                ("pg_identity_increment", "identity_increment"),
                ("pg_identity_min", "identity_min"),
                ("pg_identity_max", "identity_max"),
            ):
                if src in model_column.pg_meta:
                    model_pg_column[dst] = model_column.pg_meta[src]
            if not model_pg_column:
                model_pg_column = None
            if model_column.pg_meta.get("pg_type"):
                model_type = {
                    "type": model_column.pg_meta["pg_type"].get("kind", model_type.get("type")),
                    "pg_type": model_column.pg_meta["pg_type"],
                }
            if model_column.pg_meta.get("pg_enum_name"):
                model_type = {"type": "enum", "enum_name": model_column.pg_meta["pg_enum_name"]}
        severity = "WARNING"
        required_flag = "--force"
        if table_snapshot.get("database_type") == "postgresql":
            classification = classify_pg_type_change(snapshot_type, model_type)
            severity = {"SAFE": "INFO", "WARN": "WARNING", "CRITICAL": "WARNING"}[classification]
            required_flag = None if classification == "SAFE" else "--force"
        if snapshot_type != model_type:
            issues.append(
                SafetyIssue(
                    severity=severity,
                    change_type="change_column_type",
                    table_name=model_table.name,
                    column_name=column_name,
                    message=(
                        f"Change type of '{model_table.name}.{column_name}' from "
                        f"{snapshot_column.get('type')} to {model_column.type}"
                    ),
                    required_flag=required_flag,
                )
            )

        if snapshot_column.get("comment") != model_column.comment:
            issues.append(
                SafetyIssue(
                    severity="INFO",
                    change_type="change_column_comment",
                    table_name=model_table.name,
                    column_name=column_name,
                    message=(
                        f"Change comment of '{model_table.name}.{column_name}'"
                    ),
                )
            )

        if snapshot_column.get("pg_column") != model_pg_column:
            issues.append(
                SafetyIssue(
                    severity="WARNING",
                    change_type="change_pg_column_meta",
                    table_name=model_table.name,
                    column_name=column_name,
                    message=(
                        f"Change PostgreSQL metadata of '{model_table.name}.{column_name}'"
                    ),
                    required_flag="--force",
                )
            )

    snap_pg_table = table_snapshot.get("pg_table") or {}
    model_pg_table = model_table.pg_table or {}
    pg_table_keys = [("fillfactor", "INFO", None, "Change fillfactor for '{table}'"),
                     ("tablespace", "WARNING", "--force", "Change tablespace for '{table}'"),
                     ("inherits", "WARNING", "--force", "Change inheritance parents for '{table}'"),
                     ("pg_excludes", "WARNING", "--force", "Change EXCLUDE constraints for '{table}'")]
    for key, severity, required_flag, msg_template in pg_table_keys:
        if snap_pg_table.get(key) != model_pg_table.get(key):
            issues.append(
                SafetyIssue(
                    severity=severity,
                    change_type=f"change_pg_table_{key}",
                    table_name=model_table.name,
                    message=msg_template.replace("{table}", model_table.name),
                    required_flag=required_flag,
                )
            )

    issues.extend(_analyze_clickhouse_options(table_snapshot, model_table))
    return issues


_CH_OPTION_KEY_MAP: dict[str, str] = {
    "ch_order_by": "clickhouse_order_by",
    "ch_partition_by": "clickhouse_partition_by",
    "ch_ttl": "clickhouse_ttl",
    "ch_engine": "clickhouse_engine",
    "ch_select_statement": "clickhouse_mv_query",
    "ch_zookeeper_path": "clickhouse_zookeeper_path",
    "ch_replica_name": "clickhouse_replica_name",
    "ch_dict_source": "clickhouse_dict_source",
    "ch_dict_layout": "clickhouse_dict_layout",
    "ch_dict_lifetime": "clickhouse_dict_lifetime",
}

_CH_OPTION_RULES: dict[str, tuple[str, str | None, str]] = {
    "ch_order_by": ("WARNING", "--force", "Change ORDER BY for '{table}'"),
    "ch_partition_by": ("WARNING", "--force", "Change PARTITION BY for '{table}'"),
    "ch_ttl": ("WARNING", "--force", "Change TTL for '{table}'"),
    "ch_engine": ("WARNING", "--force", "Change engine for '{table}'"),
    "ch_select_statement": ("WARNING", "--force", "Change materialized view query for '{table}'"),
    "ch_zookeeper_path": ("WARNING", "--force", "Change ZooKeeper path for '{table}'"),
    "ch_replica_name": ("WARNING", "--force", "Change replica name for '{table}'"),
    "ch_dict_source": ("WARNING", "--force", "Change dictionary source for '{table}'"),
    "ch_dict_layout": ("WARNING", "--force", "Change dictionary layout for '{table}'"),
    "ch_dict_lifetime": ("WARNING", "--force", "Change dictionary lifetime for '{table}'"),
}


def _analyze_clickhouse_options(table_snapshot: dict[str, Any], model_table: ModelTable) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    snapshot_options = table_snapshot.get("clickhouse_options", {})
    model_options = model_table.clickhouse_options
    if not snapshot_options and not model_options:
        return issues

    for ch_key, (severity, required_flag, template) in _CH_OPTION_RULES.items():
        model_val = _normalize_option_value(model_options.get(ch_key))
        # Try ch_* first, fall back to clickhouse_* for backward compat
        snap_key = ch_key
        snap_val = _normalize_option_value(snapshot_options.get(snap_key))
        if snap_val is None and snap_key in _CH_OPTION_KEY_MAP:
            snap_val = _normalize_option_value(snapshot_options.get(_CH_OPTION_KEY_MAP[snap_key]))

        if snap_val != model_val:
            if snap_val is None and model_val is None:
                continue
            issues.append(
                SafetyIssue(
                    severity=severity,
                    change_type=_CH_OPTION_KEY_MAP.get(ch_key, ch_key),
                    table_name=model_table.name,
                    message=template.format(table=model_table.name),
                    required_flag=required_flag,
                )
            )

    model_projections_raw = model_options.get("ch_projections") or []
    model_projections = set()
    for proj in model_projections_raw:
        if isinstance(proj, dict):
            model_projections.add(proj["name"])
        elif hasattr(proj, "name"):
            model_projections.add(proj.name)

    snapshot_projections_raw = snapshot_options.get("ch_projections") or snapshot_options.get("clickhouse_projections") or []
    snapshot_projections = set()
    for proj in snapshot_projections_raw:
        if isinstance(proj, dict):
            snapshot_projections.add(proj["name"])
        elif hasattr(proj, "name"):
            snapshot_projections.add(proj.name)

    for projection_name in sorted(model_projections - snapshot_projections):
        issues.append(
            SafetyIssue(
                severity="INFO",
                change_type="add_projection",
                table_name=model_table.name,
                message=f"Add projection '{projection_name}' to '{model_table.name}'",
            )
        )

    for projection_name in sorted(snapshot_projections - model_projections):
        issues.append(
            SafetyIssue(
                severity="WARNING",
                change_type="drop_projection",
                table_name=model_table.name,
                message=f"Drop projection '{projection_name}' from '{model_table.name}'",
                required_flag="--force",
            )
        )

    return issues


def load_issues(database: str | None = None) -> list[SafetyIssue]:
    from dbwarden.config import get_database

    config = get_database(database)
    model_tables = get_all_model_tables(config.model_paths, db_name=database)
    validate_model_tables_exist(model_tables, config.model_tables, database or "default")
    model_tables = filter_model_tables_by_name(model_tables, config.model_tables)
    schema_snapshot = extract_schema_snapshot(database=database)
    return analyze_schema(model_tables, schema_snapshot)


def issues_to_json(issues: list[SafetyIssue]) -> str:
    return json.dumps([asdict(issue) for issue in issues], indent=2)


CH_COLUMN_CRITICAL = frozenset({"ch_type", "ch_low_cardinality", "ch_nullable"})
CH_COLUMN_WARN = frozenset({"ch_codec", "ch_default_expression", "ch_materialized", "ch_alias", "ch_ttl"})


def classify_ch_column_change(key: str) -> Safety:
    if key in CH_COLUMN_CRITICAL:
        return Safety.CRITICAL
    if key in CH_COLUMN_WARN:
        return Safety.WARN
    return Safety.INFO


CH_OPTION_CRITICAL = frozenset({
    "ch_engine_raw", "ch_order_by", "ch_object_type",
    "ch_select_statement", "ch_to_table", "ch_dictionary",
})
CH_OPTION_WARN = frozenset({
    "ch_partition_by", "ch_settings", "ch_zookeeper_path", "ch_replica_name",
    "ch_dict_layout", "ch_dict_source", "ch_dict_lifetime", "ch_dict_primary_key",
})


def classify_ch_options_change(key: str) -> Safety:
    if key in CH_OPTION_CRITICAL:
        return Safety.CRITICAL
    if key in CH_OPTION_WARN:
        return Safety.WARN
    return Safety.INFO


def classify_ch_safety(
    op: dict,
    model_column: Any = None,
    snapshot_column: Any = None,
) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    if op["type"] == "alter_ch_column":
        for key, change in op.get("ch_options", {}).items():
            issues.append(SafetyIssue(
                change_type="change_ch_column",
                table_name=op["table"],
                column_name=op["column"],
                severity=classify_ch_column_change(key),
                message=f"CH column {op['column']} {key}: {change.get('from')} -> {change.get('to')}",
            ))
    elif op["type"] == "alter_ch_options":
        for key, change in op.get("ch_options", {}).items():
            issues.append(SafetyIssue(
                change_type="change_ch_options",
                table_name=op["table"],
                severity=classify_ch_options_change(key),
                message=f"CH option {key}: {change.get('from')} -> {change.get('to')}",
            ))
    elif op["type"] == "drop_table" and op.get("object_type") == "materialized_view":
        issues.append(SafetyIssue(
            change_type="drop_materialized_view",
            table_name=op["table"],
            severity="CRITICAL",
            message=f"Dropping materialized view {op['table']} will lose the transformation logic",
        ))
    elif op["type"] == "recreate_ch_table" and op.get("dependent_mvs"):
        for mv in op["dependent_mvs"]:
            issues.append(SafetyIssue(
                severity="INFO",
                change_type="detach_reattach_materialized_view",
                table_name=op["table"],
                message=f"Materialized view '{mv}' will be detached before and reattached after recreating '{op['table']}'",
            ))
    elif op["type"] == "recreate_ch_table" and op.get("to_table", {}).get("object_type") == "dictionary":
        issues.append(SafetyIssue(
            severity="CRITICAL",
            change_type="recreate_dictionary",
            table_name=op["table"],
            message=f"Dictionary '{op['table']}' will be dropped and recreated, losing any cached data",
        ))
    elif op["type"] == "recreate_ch_table" and (
        op.get("from_table", {}).get("object_type") == "materialized_view"
        or op.get("to_table", {}).get("object_type") == "materialized_view"
    ):
        issues.append(SafetyIssue(
            severity="CRITICAL",
            change_type="recreate_materialized_view",
            table_name=op["table"],
            message=f"Materialized view '{op['table']}' will be dropped and recreated, losing any accumulated data",
        ))
    return issues
