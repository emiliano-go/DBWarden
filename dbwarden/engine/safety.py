from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from sqlalchemy import text

from dbwarden.database.connection import get_db_connection
from dbwarden.engine.model_discovery import ModelTable, get_all_model_tables
from dbwarden.models import SafetyIssue


def _normalize_option_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    return value


def extract_schema_snapshot(database: str | None = None) -> dict[str, dict[str, Any]]:
    from dbwarden.config import get_database

    config = get_database(database)
    if config.database_type == "clickhouse":
        return _extract_clickhouse_schema_snapshot(database)
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


def _extract_clickhouse_schema_snapshot(database: str | None = None) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    with get_db_connection(database) as connection:
        rows = connection.execute(
            text(
                "SELECT name, engine, sorting_key, primary_key, partition_key, sampling_key, create_table_query "
                "FROM system.tables WHERE database = currentDatabase()"
            )
        ).fetchall()
        for row in rows:
            table_name = row.name
            columns = connection.execute(
                text(
                    "SELECT name, type, default_expression FROM system.columns "
                    "WHERE database = currentDatabase() AND table = :table_name"
                ),
                parameters={"table_name": table_name},
            ).fetchall()
            create_query = getattr(row, "create_table_query", "") or ""
            engine = getattr(row, "engine", "") or ""

            if engine.upper() == "DICTIONARY":
                object_type = "dictionary"
            elif create_query.upper().startswith("CREATE MATERIALIZED VIEW"):
                object_type = "materialized_view"
            else:
                object_type = "table"

            snapshot[table_name] = {
                "object_type": object_type,
                "columns": {
                    col.name: {
                        "type": col.type,
                        "nullable": col.type.startswith("Nullable("),
                        "default": getattr(col, "default_expression", None),
                    }
                    for col in columns
                },
                "clickhouse_options": {
                    "clickhouse_engine": engine if engine.upper() != "DICTIONARY" else None,
                    "clickhouse_order_by": _parse_tuple_expression(getattr(row, "sorting_key", None)),
                    "clickhouse_primary_key": _parse_tuple_expression(getattr(row, "primary_key", None)),
                    "clickhouse_partition_by": _clean_expression(getattr(row, "partition_key", None)),
                    "clickhouse_sample_by": _clean_expression(getattr(row, "sampling_key", None)),
                    "clickhouse_ttl": _parse_ttl_expressions(create_query),
                    "clickhouse_projections": _parse_projection_names(create_query),
                    "clickhouse_mv_query": _parse_mv_query(create_query),
                    "clickhouse_zookeeper_path": _parse_zookeeper_path(create_query, engine),
                    "clickhouse_replica_name": _parse_replica_name(create_query, engine),
                },
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
    return value_str


def _parse_ttl_expressions(create_query: str) -> list[str]:
    ttl_match = re.search(
        r"\bTTL\s+(.+?)(?:\n(?:SETTINGS|COMMENT|AS|PRIMARY KEY|ORDER BY|PARTITION BY|SAMPLE BY)\b|$)",
        create_query,
        re.IGNORECASE | re.DOTALL,
    )
    if not ttl_match:
        return []
    ttl_body = ttl_match.group(1).strip()
    return [part.strip() for part in ttl_body.split(",") if part.strip()]


def _parse_projection_names(create_query: str) -> list[str]:
    return re.findall(r"PROJECTION\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", create_query, re.IGNORECASE)


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
        if str(snapshot_column.get("type")) != model_column.type:
            issues.append(
                SafetyIssue(
                    severity="WARNING",
                    change_type="change_column_type",
                    table_name=model_table.name,
                    column_name=column_name,
                    message=(
                        f"Change type of '{model_table.name}.{column_name}' from "
                        f"{snapshot_column.get('type')} to {model_column.type}"
                    ),
                    required_flag="--force",
                )
            )

    issues.extend(_analyze_clickhouse_options(table_snapshot, model_table))
    return issues


def _analyze_clickhouse_options(table_snapshot: dict[str, Any], model_table: ModelTable) -> list[SafetyIssue]:
    issues: list[SafetyIssue] = []
    snapshot_options = table_snapshot.get("clickhouse_options", {})
    model_options = model_table.clickhouse_options
    if not snapshot_options and not model_options:
        return issues

    option_rules = {
        "clickhouse_order_by": ("ERROR", None, "Change ORDER BY for '{table}'"),
        "clickhouse_partition_by": ("ERROR", None, "Change PARTITION BY for '{table}'"),
        "clickhouse_ttl": ("WARNING", "--force", "Change TTL for '{table}'"),
        "clickhouse_engine": ("WARNING", "--force", "Change engine for '{table}'"),
        "clickhouse_mv_query": ("WARNING", "--force", "Change materialized view query for '{table}'"),
        "clickhouse_mv_populate": ("WARNING", "--force", "Enable POPULATE for materialized view '{table}'"),
        "clickhouse_zookeeper_path": ("WARNING", "--force", "Change ZooKeeper path for '{table}'"),
        "clickhouse_replica_name": ("WARNING", "--force", "Change replica name for '{table}'"),
        "clickhouse_dict_source": ("WARNING", "--force", "Change dictionary source for '{table}'"),
        "clickhouse_dict_layout": ("WARNING", "--force", "Change dictionary layout for '{table}'"),
        "clickhouse_dict_lifetime": ("WARNING", "--force", "Change dictionary lifetime for '{table}'"),
    }

    for key, (severity, required_flag, template) in option_rules.items():
        if _normalize_option_value(snapshot_options.get(key)) != _normalize_option_value(model_options.get(key)):
            if snapshot_options.get(key) is None and model_options.get(key) is None:
                continue
            issues.append(
                SafetyIssue(
                    severity=severity,
                    change_type=key,
                    table_name=model_table.name,
                    message=template.format(table=model_table.name),
                    required_flag=required_flag,
                )
            )

    snapshot_projections = set(snapshot_options.get("clickhouse_projections") or [])
    model_projections = {
        projection["name"]
        for projection in (model_options.get("clickhouse_projections") or [])
    }

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
    model_tables = get_all_model_tables(db_name=database)
    schema_snapshot = extract_schema_snapshot(database=database)
    return analyze_schema(model_tables, schema_snapshot)


def issues_to_json(issues: list[SafetyIssue]) -> str:
    return json.dumps([asdict(issue) for issue in issues], indent=2)
