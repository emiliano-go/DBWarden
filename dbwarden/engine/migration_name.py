from dataclasses import dataclass
from typing import Optional


@dataclass
class Change:
    operation: str
    table: str
    target: Optional[str] = None
    resolved_from: Optional[str] = None
    index_type: Optional[str] = None


def autogenerate_migration_name(changes: list[Change]) -> str:
    if not changes:
        return ""

    if len(changes) == 1:
        return _single_change(changes[0])

    changes_by_table: dict[str, list[Change]] = {}
    for change in changes:
        changes_by_table.setdefault(change.table, []).append(change)

    if len(changes_by_table) == 1:
        table_name = list(changes_by_table.keys())[0]
        table_changes = changes_by_table[table_name]
        return _single_table_multiple_changes(table_name, table_changes)

    return _multiple_tables(changes_by_table)


def _single_change(change: Change) -> str:
    if change.target:
        target = change.target
        if change.index_type and change.index_type != "btree":
            target = f"{target}_{change.index_type}"
        return _truncate(f"{change.operation}_{change.table}_{target}")
    return _truncate(f"{change.operation}_{change.table}")


def _single_table_multiple_changes(table: str, changes: list[Change]) -> str:
    operations = set(c.operation for c in changes)
    targets = [c.target for c in changes if c.target]

    if len(operations) == 1 and len(targets) >= 1:
        operation = _pluralize(list(operations)[0])
        if len(targets) == 1:
            return _truncate(f"{operation}_{table}_{targets[0]}")
        if len(targets) == 2:
            return _truncate(f"{operation}_{table}_{targets[0]}_{targets[1]}")
        num_more = len(targets) - 2
        return _truncate(f"{operation}_{table}_{targets[0]}_{targets[1]}_and_{num_more}_more")

    if len(targets) >= 1:
        if len(targets) == 2:
            return _truncate(f"alter_{table}_{targets[0]}_{targets[1]}")
        if len(targets) >= 3:
            num_more = len(targets) - 2
            return _truncate(f"alter_{table}_{targets[0]}_{targets[1]}_and_{num_more}_more")
        return _truncate(f"alter_{table}_{targets[0]}")

    return _truncate(f"alter_{table}")


def _multiple_tables(changes_by_table: dict[str, list[Change]]) -> str:
    table_change_counts = [(table, len(chgs)) for table, chgs in changes_by_table.items()]
    table_change_counts.sort(key=lambda x: -x[1])
    primary_table = table_change_counts[0][0]
    num_more_tables = len(table_change_counts) - 1

    primary_changes = changes_by_table[primary_table]
    operations = set(c.operation for c in primary_changes)
    targets = [c.target for c in primary_changes if c.target]
    table_level_ops = [c for c in primary_changes if c.target is None]
    all_operations = set()
    for chgs in changes_by_table.values():
        all_operations.update(c.operation for c in chgs)

    if not targets and table_level_ops and len(operations) == 1:
        operation = list(operations)[0]
        if len(changes_by_table) == 2:
            tables = list(changes_by_table.keys())
            plural_op = _pluralize(operation)
            return _truncate(f"{plural_op}_{tables[0]}_{tables[1]}")
        plural_op = _pluralize(operation)
        return _truncate(f"{plural_op}_{primary_table}_and_{num_more_tables}_more_tables")

    if not targets and len(all_operations) == 1 and len(changes_by_table) >= 2:
        all_tables = list(changes_by_table.keys())
        operation = list(all_operations)[0]
        plural_op = _pluralize(operation)
        if len(all_tables) == 2:
            return _truncate(f"{plural_op}_{all_tables[0]}_{all_tables[1]}")
        return _truncate(f"{plural_op}_{primary_table}_and_{num_more_tables}_more_tables")

    if targets:
        all_ops = set()
        for chgs in changes_by_table.values():
            all_ops.update(c.operation for c in chgs)
        
        if len(all_ops) == 1:
            operation = list(all_ops)[0]
        else:
            operation = "alter"

        if len(targets) >= 1:
            first_target = targets[0]
            if len(targets) == 2:
                return _truncate(f"{operation}_{primary_table}_{first_target}_{targets[1]}_and_{num_more_tables}_more_tables")
            if len(targets) >= 3:
                num_more_targets = len(targets) - 2
                return _truncate(f"{operation}_{primary_table}_{first_target}_{targets[1]}_and_{num_more_targets}_more_targets_and_{num_more_tables}_more_tables")
            return _truncate(f"{operation}_{primary_table}_{first_target}_and_{num_more_tables}_more_tables")
        return f"alter_{primary_table}_and_{num_more_tables}_more_tables"

    if len(primary_changes) >= 2:
        first_target = primary_changes[0].target or primary_table
        remaining = len(primary_changes) - 1
        return f"alter_{primary_table}_{first_target}_and_{remaining}_more"

    return _truncate(f"alter_{primary_table}_and_{num_more_tables}_more_tables")


def _pluralize(operation: str) -> str:
    singular_to_plural = {
        "add_column": "add_columns",
        "drop_column": "drop_columns",
        "rename_column": "rename_columns",
        "create_table": "create_tables",
        "drop_table": "drop_tables",
        "add_index": "add_indexes",
        "drop_index": "drop_indexes",
        "add_foreign_key": "add_foreign_keys",
        "drop_foreign_key": "drop_foreign_keys",
        "add_constraint": "add_constraints",
        "drop_constraint": "drop_constraints",
        "alter_column_type": "alter_column_types",
        "alter_column_nullable": "alter_column_nullables",
        "alter_column_default": "alter_column_defaults",
    }
    return singular_to_plural.get(operation, operation + "s")


def _truncate(name: str) -> str:
    if len(name) <= 72:
        return name

    parts = name.split("_")
    op_words = {"add", "drop", "alter", "create", "rename", "adds", "drops", "alters", "creates", "renames",
               "add_columns", "drop_columns", "rename_columns", "create_tables", "drop_tables",
               "add_indexes", "drop_indexes", "add_foreign_keys", "drop_foreign_keys",
               "add_constraints", "drop_constraints",
               "alter_column_type", "alter_column_types",
               "alter_column_nullable", "alter_column_nullables",
               "alter_column_default", "alter_column_defaults"}
    
    operation = []
    identifiers = []
    in_op = True
    
    for part in parts:
        if in_op and part in op_words:
            operation.append(part)
        else:
            in_op = False
            identifiers.append(part)
    
    result_parts = operation.copy()
    remaining = 72 - len("_".join(result_parts)) - 1
    
    for id_part in identifiers:
        if remaining <= 0:
            break
        if len(id_part) > remaining:
            result_parts.append(id_part[:remaining])
            break
        else:
            result_parts.append(id_part)
            remaining -= (len(id_part) + 1)
    
    return "_".join(result_parts)