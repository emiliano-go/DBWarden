import sys
from typing import Any


def _resolve_clickhouse_recreate_ops(
    upgrade_ops: list[dict[str, Any]],
    rollback_ops: list[dict[str, Any]],
    clickhouse_engine_recreate: bool,
    drop_preserved_clickhouse_table: bool | None,
) -> None:
    recreate_ops = [op for op in upgrade_ops if op.get("type") == "recreate_ch_table"]
    if not recreate_ops:
        return
    if not clickhouse_engine_recreate:
        tables = ", ".join(sorted(op["table"] for op in recreate_ops))
        raise ValueError(
            f"ClickHouse engine change detected for {tables}. Rerun with --clickhouse-engine-recreate to generate a rebuild migration."
        )

    drop_old = drop_preserved_clickhouse_table
    if drop_old is None and sys.stdin.isatty():
        answer = input(
            "Drop preserved old ClickHouse table after swap? [y/N]: "
        ).strip().lower()
        drop_old = answer in ("y", "yes")
    if drop_old is None:
        drop_old = False

    for op in upgrade_ops:
        if op.get("type") == "recreate_ch_table":
            op["drop_old_after_swap"] = drop_old
    for op in rollback_ops:
        if op.get("type") == "recreate_ch_table":
            op["drop_old_after_swap"] = drop_old


def _check_recreate_rename_conflict(
    ops: list[dict[str, Any]],
    confirmed_table_intents: set[tuple[str, str]],
) -> None:
    recreate_tables = {op["table"] for op in ops if op.get("type") == "recreate_ch_table"}
    rename_old_tables = {old for old, _ in confirmed_table_intents}
    conflict = recreate_tables & rename_old_tables
    if conflict:
        names = ", ".join(sorted(conflict))
        raise ValueError(
            f"Table(s) {names} have both a rename and an engine change in the same migration. "
            "Perform the rename and engine change as separate migrations."
        )
