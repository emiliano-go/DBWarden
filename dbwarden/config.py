from __future__ import annotations

import ast
import importlib
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.engine import make_url

from dbwarden.config_registry import register_reset_hook, registered_entries, reset_registry
from dbwarden.config_schema import DatabaseEntry
from dbwarden.constants import TOML_FILE
from dbwarden.exceptions import ConfigurationError

DatabaseType = Literal["sqlite", "postgresql", "mysql", "mariadb", "clickhouse"]
DEFAULT_MIGRATION_TABLE = "_dbwarden_migrations"

_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "site",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}


@dataclass
class DatabaseConfig:
    sqlalchemy_url: str
    database_type: DatabaseType
    secure_values: bool = False
    secure_display_values: dict[str, str] = field(default_factory=dict)
    model_paths: list[str] | None = None
    migrations_dir: str = "migrations"
    migration_table: str = DEFAULT_MIGRATION_TABLE
    postgres_schema: str | None = None
    dev_database_url: str | None = None
    dev_database_type: DatabaseType | None = None
    overlap_models: bool = False


@dataclass
class MultiDbConfig:
    databases: dict[str, DatabaseConfig] = field(default_factory=dict)
    default: str = "default"


@dataclass
class _ResolvedSource:
    kind: Literal["file", "module"]
    value: str


_USE_DEV_DATABASE = False
_STRICT_TRANSLATION = False
_RESOLVED_SOURCE_CACHE: _ResolvedSource | None = None


def set_dev_mode(enabled: bool) -> None:
    global _USE_DEV_DATABASE
    _USE_DEV_DATABASE = enabled


def is_dev_mode() -> bool:
    return _USE_DEV_DATABASE


def set_strict_translation(enabled: bool) -> None:
    global _STRICT_TRANSLATION
    _STRICT_TRANSLATION = enabled


def is_strict_translation() -> bool:
    return _STRICT_TRANSLATION


def _clear_source_cache() -> None:
    global _RESOLVED_SOURCE_CACHE
    _RESOLVED_SOURCE_CACHE = None


register_reset_hook(_clear_source_cache)


def get_toml_path() -> Path | None:
    """Backward-compatible helper retained for callers.

    TOML is no longer the primary source. This returns path if present
    but runtime config loading does not depend on it.
    """

    current = Path.cwd().resolve()
    while True:
        toml_path = current / TOML_FILE
        if toml_path.exists():
            return toml_path
        if current.parent == current:
            break
        current = current.parent
    return None


def _infer_database_type(sqlalchemy_url: str) -> DatabaseType:
    url_lower = sqlalchemy_url.lower()
    if url_lower.startswith("sqlite"):
        return "sqlite"
    if url_lower.startswith("postgresql") or url_lower.startswith("postgres"):
        return "postgresql"
    if url_lower.startswith("mysql"):
        return "mysql"
    if url_lower.startswith("mariadb"):
        return "mariadb"
    if url_lower.startswith("clickhouse"):
        return "clickhouse"
    return "sqlite"


def _normalized_url(url: str) -> str:
    try:
        parsed = make_url(url)
        return parsed.render_as_string(hide_password=False)
    except Exception:
        return url.strip()


def _build_database_target_key(url: str, db_type: str, base_dir: Path) -> str:
    parsed = make_url(url)

    if db_type == "sqlite":
        db_path = parsed.database or ""
        if db_path == ":memory:" or not db_path:
            return f"sqlite::{db_path or ':memory:'}"

        normalized_path = Path(db_path)
        if not normalized_path.is_absolute():
            normalized_path = (base_dir / normalized_path).resolve()
        else:
            normalized_path = normalized_path.resolve()

        return f"sqlite::{normalized_path.as_posix()}"

    host = parsed.host or ""
    port = str(parsed.port or "")
    database = parsed.database or ""
    return f"{db_type}::{host}:{port}/{database}"


def _discover_dbwarden_files(root: Path) -> list[Path]:
    matches: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        if "dbwarden.py" in files:
            matches.append(Path(current) / "dbwarden.py")
    return sorted(matches)


def _workspace_root() -> Path:
    current = Path.cwd().resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return Path.cwd().resolve()
        current = current.parent


def _file_has_database_config_call(path: Path) -> bool:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except Exception:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "database_config":
                return True
    return False


def _full_scan_database_config_calls(root: Path) -> list[Path]:
    matches: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = Path(current) / filename
            if _file_has_database_config_call(path):
                matches.append(path)
    return sorted(matches)


def _is_literal_node(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_literal_node(el) for el in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            (k is None or _is_literal_node(k)) and _is_literal_node(v)
            for k, v in zip(node.keys, node.values)
        )
    return False


def _extract_variable_value_expressions(path: Path) -> list[dict[str, str]]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return []

    call_metadata: list[dict[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Name) or call.func.id != "database_config":
            continue

        variable_kwargs: dict[str, str] = {}
        for kw in call.keywords:
            if kw.arg is None:
                continue
            if _is_literal_node(kw.value):
                continue
            expr = ast.get_source_segment(source, kw.value)
            if expr is None:
                expr = ast.unparse(kw.value)
            variable_kwargs[kw.arg] = expr.strip()
        call_metadata.append(variable_kwargs)
    return call_metadata


def _resolve_source() -> _ResolvedSource:
    global _RESOLVED_SOURCE_CACHE
    if _RESOLVED_SOURCE_CACHE is not None:
        return _RESOLVED_SOURCE_CACHE

    root = _workspace_root()
    dbwarden_files = _discover_dbwarden_files(root)
    if len(dbwarden_files) > 1:
        # Use relative paths to avoid leaking directory structure
        rel_paths = [str(p.relative_to(root)) for p in dbwarden_files]
        paths = "\n".join(rel_paths)
        raise ConfigurationError(
            "Multiple dbwarden.py files found. Keep exactly one.\n" + paths
        )
    if len(dbwarden_files) == 1:
        _RESOLVED_SOURCE_CACHE = _ResolvedSource("file", str(dbwarden_files[0]))
        return _RESOLVED_SOURCE_CACHE

    callsite_files = _full_scan_database_config_calls(root)
    if len(callsite_files) > 1:
        # Use relative paths to avoid leaking directory structure
        rel_paths = [str(p.relative_to(root)) for p in callsite_files]
        paths = "\n".join(rel_paths)
        raise ConfigurationError(
            "Multiple database_config(...) call sites found. Keep exactly one source or set DBWARDEN_CONFIG_MODULE.\n"
            + paths
        )
    if len(callsite_files) == 1:
        _RESOLVED_SOURCE_CACHE = _ResolvedSource("file", str(callsite_files[0]))
        return _RESOLVED_SOURCE_CACHE

    module_name = os.getenv("DBWARDEN_CONFIG_MODULE")
    if module_name:
        _RESOLVED_SOURCE_CACHE = _ResolvedSource("module", module_name)
        return _RESOLVED_SOURCE_CACHE

    raise ConfigurationError(
        "No configuration found. Add database_config(...) call(s), create dbwarden.py with dbwarden init, "
        "or set DBWARDEN_CONFIG_MODULE."
    )


def get_settings_source_file() -> Path:
    """Return resolved settings source file for mutating commands."""
    source = _resolve_source()
    if source.kind != "file":
        raise ConfigurationError(
            "Settings mutator commands require a file-based config source. "
            "Use a local dbwarden.py or full-scan-resolved file source."
        )
    return Path(source.value)


def _import_source(source: _ResolvedSource) -> Path:
    if source.kind == "module":
        importlib.import_module(source.value)
        return Path.cwd().resolve()

    path = Path(source.value)
    base_dir = path.parent.resolve()

    from dbwarden.sandbox import load_config_module

    load_config_module(path, base_dir)
    return base_dir


def _entry_model_paths(entry: DatabaseEntry) -> set[str]:
    return {p for p in (entry.model_paths or [])}


def _finalize_entries(
    entries: list[DatabaseEntry],
    base_dir: Path,
    variable_value_expressions: list[dict[str, str]] | None = None,
) -> MultiDbConfig:
    if not entries:
        raise ConfigurationError(
            "No database_config(...) call found. Add dbwarden init or set DBWARDEN_CONFIG_MODULE."
        )

    defaults = [e for e in entries if e.default]
    if len(defaults) != 1:
        raise ConfigurationError(
            f"Exactly one default=True required, found {len(defaults)}"
        )

    if len(entries) > 1:
        missing_model_paths = [e.database_name for e in entries if not e.model_paths]
        if missing_model_paths:
            names = ", ".join(missing_model_paths)
            raise ConfigurationError(
                f"model_paths is required when more than one database is configured. Missing for: {names}"
            )

    databases: dict[str, DatabaseConfig] = {}
    url_owners: dict[str, str] = {}
    migration_owners: dict[str, str] = {}
    target_owners: dict[str, str] = {}

    for index, entry in enumerate(entries):
        if entry.database_name in databases:
            raise ConfigurationError(f"Duplicate database_name: '{entry.database_name}'")

        migrations_dir = entry.migrations_dir or f"migrations/{entry.database_name}"
        if migrations_dir in migration_owners:
            raise ConfigurationError(
                f"Duplicate migrations_dir: '{migrations_dir}' in '{entry.database_name}' and '{migration_owners[migrations_dir]}'"
            )
        migration_owners[migrations_dir] = entry.database_name

        normalized_url = _normalized_url(entry.database_url)
        if normalized_url in url_owners:
            raise ConfigurationError(
                f"Duplicate database_url: '{entry.database_url}'"
            )
        url_owners[normalized_url] = entry.database_name

        target_key = _build_database_target_key(
            entry.database_url,
            entry.database_type,
            base_dir,
        )
        if target_key in target_owners:
            raise ConfigurationError(
                "Duplicate database target detected: "
                f"'{entry.database_name}' collides with '{target_owners[target_key]}'"
            )
        target_owners[target_key] = entry.database_name

        if entry.dev_database_type and not entry.dev_database_url:
            raise ConfigurationError(
                f"dev_database_url is required when dev_database_type is set for '{entry.database_name}'"
            )

        if entry.dev_database_url:
            dev_url_key = _normalized_url(entry.dev_database_url)
            owner = url_owners.get(dev_url_key)
            if owner is not None:
                raise ConfigurationError(
                    f"Duplicate dev_database_url: '{entry.dev_database_url}'"
                )
            url_owners[dev_url_key] = entry.database_name

            dev_type = entry.dev_database_type or _infer_database_type(
                entry.dev_database_url
            )
            dev_target_key = _build_database_target_key(
                entry.dev_database_url,
                dev_type,
                base_dir,
            )
            if dev_target_key in target_owners:
                raise ConfigurationError(
                    "Duplicate database target detected for dev database: "
                    f"'{entry.database_name}' collides with '{target_owners[dev_target_key]}'"
                )
            target_owners[dev_target_key] = entry.database_name

        secure_display_values: dict[str, str] = {}
        if entry.secure_values and variable_value_expressions is not None:
            if index < len(variable_value_expressions):
                secure_display_values = variable_value_expressions[index]

        databases[entry.database_name] = DatabaseConfig(
            sqlalchemy_url=entry.database_url,
            database_type=entry.database_type,
            secure_values=entry.secure_values,
            secure_display_values=secure_display_values,
            model_paths=entry.model_paths,
            migrations_dir=migrations_dir,
            migration_table=entry.migration_table or DEFAULT_MIGRATION_TABLE,
            postgres_schema=None,
            dev_database_url=entry.dev_database_url,
            dev_database_type=entry.dev_database_type,
            overlap_models=entry.overlap_models,
        )

    # model_paths overlap validation
    for i, left in enumerate(entries):
        for right in entries[i + 1 :]:
            if left.overlap_models or right.overlap_models:
                continue
            overlap = _entry_model_paths(left).intersection(_entry_model_paths(right))
            if overlap:
                overlap_path = sorted(overlap)[0]
                raise ConfigurationError(
                    "model_paths overlap detected: "
                    f"path '{overlap_path}' from '{right.database_name}' is also defined in '{left.database_name}'; "
                    "set overlap_models=True to allow"
                )

    default_name = defaults[0].database_name
    return MultiDbConfig(databases=databases, default=default_name)


def get_multi_db_config() -> MultiDbConfig:
    source = _resolve_source()
    variable_value_expressions: list[dict[str, str]] | None = None
    if source.kind == "file":
        variable_value_expressions = _extract_variable_value_expressions(
            Path(source.value)
        )
    reset_registry()
    base_dir = _import_source(source)
    entries = registered_entries()
    return _finalize_entries(entries, base_dir, variable_value_expressions)


def display_value(db: DatabaseConfig, field_name: str, value: Any) -> Any:
    if db.secure_values and field_name in db.secure_display_values:
        return db.secure_display_values[field_name]
    return value


def get_database(name: str | None = None) -> DatabaseConfig:
    config = get_multi_db_config()

    if name is None:
        name = config.default

    if name not in config.databases:
        available = list(config.databases.keys())
        raise ConfigurationError(
            f"Database '{name}' not found in settings config. Available databases: {available}"
        )

    selected = config.databases[name]

    if not is_dev_mode():
        return selected

    if not selected.dev_database_url:
        raise ConfigurationError(
            f"--dev mode is enabled, but database '{name}' has no dev_database_url configured."
        )

    dev_database_type = selected.dev_database_type or _infer_database_type(
        selected.dev_database_url
    )

    return replace(
        selected,
        sqlalchemy_url=selected.dev_database_url,
        database_type=dev_database_type,
    )


def list_databases() -> list[str]:
    return list(get_multi_db_config().databases.keys())


def get_config() -> DatabaseConfig:
    return get_database(None)
