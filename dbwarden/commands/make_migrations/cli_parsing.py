from dataclasses import dataclass
from typing import Any


@dataclass
class RenameIntent:
    table: str
    old_name: str
    new_name: str


def _parse_rename_flags(flags: list[str]) -> list[RenameIntent]:
    intents: list[RenameIntent] = []
    for flag in flags:
        parts = flag.split(".", 1)
        if len(parts) != 2 or ":" not in parts[1]:
            raise ValueError(
                f"Invalid --rename format: {flag!r}. Expected table.old_name:new_name"
            )
        table = parts[0]
        old_new = parts[1].split(":", 1)
        if len(old_new) != 2 or not old_new[0] or not old_new[1]:
            raise ValueError(
                f"Invalid --rename format: {flag!r}. Expected table.old_name:new_name"
            )
        intents.append(RenameIntent(table=table, old_name=old_new[0], new_name=old_new[1]))
    return intents


def _format_rename_warning(intents: list[tuple[str, str, str, str]]) -> str:
    lines = [
        "The following auto-detected column renames were not confirmed:"
    ]
    for tbl, old, new, _flag_example in intents:
        lines.append(
            f"  {tbl}.{old} \u2192 {new} (use --rename {tbl}.{old}:{new} to confirm)"
        )
    lines.append("These will be emitted as DROP + ADD instead of RENAME.")
    return "\n".join(lines)


def _parse_rename_table_flags(raw_flags: list[str]) -> list[dict[str, str]]:
    intents: list[dict[str, str]] = []
    for flag in raw_flags:
        if ":" not in flag:
            raise ValueError(
                f"Invalid --rename-table format: '{flag}'. "
                f"Expected: old_table:new_table"
            )
        old_table, new_table = flag.split(":", 1)
        old_table = old_table.strip()
        new_table = new_table.strip()
        if not old_table or not new_table:
            raise ValueError(
                f"Invalid --rename-table format: '{flag}'. "
                f"Expected: old_table:new_table"
            )
        intents.append({"old_table": old_table, "new_table": new_table})
    return intents


def _validate_table_rename_intents(
    intents: list[dict[str, str]],
    snapshot: dict[str, Any],
    model_table_names: set[str],
) -> None:
    snapshot_tables = set(snapshot.get("tables", {}).keys())
    for intent in intents:
        if intent["old_table"] not in snapshot_tables:
            raise ValueError(
                f"--rename-table: table '{intent['old_table']}' does not exist "
                f"in latest snapshot."
            )
        if intent["new_table"] in snapshot_tables:
            raise ValueError(
                f"--rename-table: table '{intent['new_table']}' already exists "
                f"in latest snapshot."
            )
        if intent["old_table"] in model_table_names:
            raise ValueError(
                f"--rename-table: '{intent['old_table']}' still present in models. "
                f"Remove it before declaring a rename."
            )
        if intent["new_table"] not in model_table_names:
            raise ValueError(
                f"--rename-table: '{intent['new_table']}' not found in models. "
                f"Add it before declaring a rename."
            )


def _format_table_rename_warning(candidates: list[tuple[str, str, float]]) -> str:
    lines = [
        "Warning: table rename candidates detected but running non-interactive. "
        "Emitting drop+add."
    ]
    for old, new, ratio in candidates:
        lines.append(f"  {old} \u2192 {new}  ({int(ratio * 100):d}% columns match)")
    lines.append("Rerun with --rename-table old:new to resolve.")
    return "\n".join(lines)
