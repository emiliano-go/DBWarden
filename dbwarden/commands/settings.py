from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from dbwarden.config import display_value, get_multi_db_config, get_settings_source_file
from dbwarden.config_registry import reset_registry
from dbwarden.config_schema import DatabaseEntry, structure_database_entry
from dbwarden.exceptions import ConfigurationError
from dbwarden.output import console


def _display_db_type(value: str) -> str:
    mapping = {
        "postgresql": "PostgreSQL",
        "sqlite": "SQLite",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "clickhouse": "ClickHouse",
    }
    return mapping.get(value, value)


def _print_field(label: str, value: Any) -> None:
    console.print("  •", style="bold magenta", end=" ")
    console.print(f"{label}:", style="bold cyan", end=" ")
    console.print(str(value), style="default", markup=False, highlight=False)


def _parse_constant(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_parse_constant(el) for el in node.elts]
    raise ConfigurationError("Unsupported value in database_config(...) call. Use literals only.")


def _extract_entries_from_file(path: Path) -> tuple[str, list[DatabaseEntry]]:
    content = path.read_text(encoding="utf-8")
    tree = ast.parse(content)
    entries: list[DatabaseEntry] = []

    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "database_config":
            continue

        kwargs: dict[str, Any] = {}
        for kw in call.keywords:
            if kw.arg is None:
                raise ConfigurationError("database_config(...) does not support **kwargs expansion.")
            kwargs[kw.arg] = _parse_constant(kw.value)

        entries.append(structure_database_entry(kwargs))

    return content, entries


def _entry_kwargs(entry: DatabaseEntry) -> dict[str, Any]:
    return {
        "database_name": entry.database_name,
        "database_type": entry.database_type,
        "database_url": entry.database_url,
        "secure_values": entry.secure_values,
        "default": entry.default,
        "migrations_dir": entry.migrations_dir,
        "migration_table": entry.migration_table,
        "model_paths": entry.model_paths,
        "dev_database_type": entry.dev_database_type,
        "dev_database_url": entry.dev_database_url,
        "overlap_models": entry.overlap_models,
    }


def _render_entry(entry: DatabaseEntry) -> str:
    kwargs = _entry_kwargs(entry)
    ordered = [
        "database_name",
        "default",
        "database_type",
        "database_url",
        "secure_values",
        "migrations_dir",
        "migration_table",
        "model_paths",
        "dev_database_type",
        "dev_database_url",
        "overlap_models",
    ]
    lines = ["database_config("]
    for key in ordered:
        value = kwargs[key]
        if value is None:
            continue
        if key == "default" and value is False:
            continue
        if key == "overlap_models" and value is False:
            continue
        lines.append(f"    {key}={value!r},")
    lines.append(")")
    return "\n".join(lines)


def _rewrite_entries(path: Path, original_content: str, entries: list[DatabaseEntry]) -> None:
    tree = ast.parse(original_content)
    lines = original_content.splitlines()
    remove_ranges: list[tuple[int, int]] = []

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "database_config":
                start = node.lineno - 1
                end = (node.end_lineno or node.lineno) - 1
                remove_ranges.append((start, end))

    keep = [True] * len(lines)
    for start, end in remove_ranges:
        for i in range(start, end + 1):
            keep[i] = False

    kept_lines = [line for i, line in enumerate(lines) if keep[i]]
    body = "\n".join(kept_lines).rstrip()

    if "from dbwarden import database_config" not in body:
        body = (
            "from dbwarden import database_config\n\n" + body if body else "from dbwarden import database_config"
        )

    rendered_entries = "\n\n".join(_render_entry(e) for e in entries)
    new_content = f"{body}\n\n{rendered_entries}\n"
    path.write_text(new_content, encoding="utf-8")


def _load_entries_for_mutation() -> tuple[Path, str, list[DatabaseEntry]]:
    path = get_settings_source_file()
    content, entries = _extract_entries_from_file(path)
    if not entries:
        raise ConfigurationError("No database_config(...) calls found to mutate.")
    return path, content, entries


def _finalize_mutation(path: Path, content: str, entries: list[DatabaseEntry]) -> None:
    _rewrite_entries(path, content, entries)
    reset_registry()
    get_multi_db_config()


def handle_settings_show(database: str | None = None, all_databases: bool = False) -> None:
    cfg = get_multi_db_config()
    if all_databases:
        console.rule("[bold yellow]DBWarden Settings[/bold yellow]")
        console.print(style="dim")

        for name, db in cfg.databases.items():
            marker = " (default)" if name == cfg.default else ""
            console.print(f"Database: {name.upper()}{marker}", style="bold yellow")
            _print_field(
                "Type",
                _display_db_type(
                    str(display_value(db, "database_type", db.database_type))
                ),
            )
            _print_field("URL", display_value(db, "database_url", db.sqlalchemy_url))
            _print_field(
                "Migrations Directory",
                display_value(db, "migrations_dir", db.migrations_dir),
            )
            _print_field(
                "Migration Table",
                display_value(db, "migration_table", db.migration_table),
            )
            _print_field("Model Paths", display_value(db, "model_paths", db.model_paths))
            _print_field(
                "Dev Database Type",
                display_value(db, "dev_database_type", db.dev_database_type),
            )
            _print_field(
                "Dev Database URL",
                display_value(db, "dev_database_url", db.dev_database_url),
            )
            _print_field(
                "Overlap Models",
                display_value(db, "overlap_models", db.overlap_models),
            )
            console.print(style="dim")
        return

    target = database or cfg.default
    if target not in cfg.databases:
        raise ConfigurationError(f"Database '{target}' not found.")
    db = cfg.databases[target]

    console.rule(f"[bold yellow]Database: {target}[/bold yellow]")

    _print_field("Default", target == cfg.default)
    _print_field(
        "Type",
        _display_db_type(str(display_value(db, "database_type", db.database_type))),
    )
    _print_field("URL", display_value(db, "database_url", db.sqlalchemy_url))
    _print_field(
        "Migrations Directory",
        display_value(db, "migrations_dir", db.migrations_dir),
    )
    _print_field(
        "Migration Table",
        display_value(db, "migration_table", db.migration_table),
    )
    _print_field("Model Paths", display_value(db, "model_paths", db.model_paths))
    _print_field(
        "Dev Database Type",
        display_value(db, "dev_database_type", db.dev_database_type),
    )
    _print_field(
        "Dev Database URL",
        display_value(db, "dev_database_url", db.dev_database_url),
    )
    _print_field("Overlap Models", display_value(db, "overlap_models", db.overlap_models))


def handle_settings_default_set(name: str) -> None:
    path, content, entries = _load_entries_for_mutation()
    found = False
    updated: list[DatabaseEntry] = []
    for entry in entries:
        is_target = entry.database_name == name
        found = found or is_target
        updated.append(
            DatabaseEntry(
                **{**_entry_kwargs(entry), "default": is_target}
            )
        )
    if not found:
        raise ConfigurationError(f"Database '{name}' not found.")
    _finalize_mutation(path, content, updated)


def handle_settings_database_add(
    name: str,
    database_type: str,
    url: str,
    migrations_dir: str | None = None,
    migration_table: str | None = None,
    model_paths: list[str] | None = None,
    dev_type: str | None = None,
    dev_url: str | None = None,
    overlap_models: bool = False,
    secure_values: bool = False,
    default: bool = False,
) -> None:
    path, content, entries = _load_entries_for_mutation()
    if any(e.database_name == name for e in entries):
        raise ConfigurationError(f"Database '{name}' already exists.")

    if default:
        entries = [DatabaseEntry(**{**_entry_kwargs(e), "default": False}) for e in entries]

    new_entry = structure_database_entry(
        {
            "database_name": name,
            "database_type": database_type,
            "database_url": url,
            "migrations_dir": migrations_dir,
            "migration_table": migration_table,
            "model_paths": model_paths,
            "dev_database_type": dev_type,
            "dev_database_url": dev_url,
            "overlap_models": overlap_models,
            "secure_values": secure_values,
            "default": default,
        }
    )
    entries.append(new_entry)
    _finalize_mutation(path, content, entries)


def handle_settings_database_remove(name: str) -> None:
    path, content, entries = _load_entries_for_mutation()
    updated = [e for e in entries if e.database_name != name]
    if len(updated) == len(entries):
        raise ConfigurationError(f"Database '{name}' not found.")
    if not updated:
        raise ConfigurationError("At least one database must remain configured.")
    if not any(e.default for e in updated):
        first = updated[0]
        updated[0] = DatabaseEntry(**{**_entry_kwargs(first), "default": True})
    _finalize_mutation(path, content, updated)


def handle_settings_database_rename(old: str, new: str) -> None:
    path, content, entries = _load_entries_for_mutation()
    if any(e.database_name == new for e in entries):
        raise ConfigurationError(f"Database '{new}' already exists.")
    updated: list[DatabaseEntry] = []
    found = False
    for e in entries:
        if e.database_name == old:
            found = True
            updated.append(DatabaseEntry(**{**_entry_kwargs(e), "database_name": new}))
        else:
            updated.append(e)
    if not found:
        raise ConfigurationError(f"Database '{old}' not found.")
    _finalize_mutation(path, content, updated)


def handle_settings_database_set_dev(name: str, dev_type: str, dev_url: str) -> None:
    path, content, entries = _load_entries_for_mutation()
    updated: list[DatabaseEntry] = []
    found = False
    for e in entries:
        if e.database_name == name:
            found = True
            updated.append(
                DatabaseEntry(
                    **{
                        **_entry_kwargs(e),
                        "dev_database_type": dev_type,
                        "dev_database_url": dev_url,
                    }
                )
            )
        else:
            updated.append(e)
    if not found:
        raise ConfigurationError(f"Database '{name}' not found.")
    _finalize_mutation(path, content, updated)


def handle_settings_database_clear_dev(name: str) -> None:
    path, content, entries = _load_entries_for_mutation()
    updated: list[DatabaseEntry] = []
    found = False
    for e in entries:
        if e.database_name == name:
            found = True
            updated.append(
                DatabaseEntry(
                    **{
                        **_entry_kwargs(e),
                        "dev_database_type": None,
                        "dev_database_url": None,
                    }
                )
            )
        else:
            updated.append(e)
    if not found:
        raise ConfigurationError(f"Database '{name}' not found.")
    _finalize_mutation(path, content, updated)
