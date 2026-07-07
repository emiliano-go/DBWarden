from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.orm import Session as SASession

from dbwarden.exceptions import SeedError
from dbwarden.logging import get_logger
from dbwarden.output import console
from dbwarden.repositories.seeds_repo import (
    create_seeds_table_if_not_exists,
    get_applied_seed_versions,
    record_applied_seed,
    remove_seed_record,
    get_seed_record,
)
from dbwarden.seed import Seed, _seed_registry, _row_to_dict

if TYPE_CHECKING:
    from dbwarden.schema._base import DBWardenMeta


def discover_code_seeds(db_name: str | None = None) -> list[type[Seed]]:
    """Discover Seed subclasses from the registry, filtered by database."""
    config_db = db_name or "default"
    return [
        cls
        for cls in _seed_registry
        if getattr(cls.__seed_meta__, "database", None) in (config_db, None)
    ]


def _get_code_seed_filename(cls: type[Seed]) -> str:
    return f"__code__.{cls.__module__}.{cls.__qualname__}"


def _get_code_seed_version(cls: type[Seed], db_name: str | None = None) -> str:
    seeds = discover_code_seeds(db_name)
    seeds.sort(key=lambda c: f"{c.__module__}.{c.__qualname__}")
    try:
        idx = seeds.index(cls)
    except ValueError:
        idx = 0
    return f"C{idx + 1:04d}"


def _compute_code_seed_checksum(cls: type[Seed]) -> str:
    source = ""
    try:
        import inspect
        source = inspect.getsource(cls)
    except (OSError, TypeError):
        pass
    return hashlib.sha256(source.encode()).hexdigest()[:16] if source else ""


def _insert_or_ignore(
    conn: Any, table: str, data: dict, conflict_columns: list[str] | None = None
) -> None:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data)
    stmt = f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({placeholders})"
    conn.execute(text(stmt), data)


def _insert_or_update(
    conn: Any, table: str, data: dict, conflict_columns: list[str] | None = None
) -> None:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data)
    updates = ", ".join(f"{k} = :{k}" for k in data.keys())
    if conflict_columns:
        conflict = ", ".join(conflict_columns)
        stmt = (
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
        )
    else:
        stmt = (
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT DO UPDATE SET {updates}"
        )
    conn.execute(text(stmt), data)


def apply_code_seed(
    cls: type[Seed],
    db_name: str | None = None,
    dry_run: bool = False,
) -> None:
    meta = cls.__seed_meta__
    if meta is None:
        raise SeedError(
            f"Seed class {cls.__name__} has no __seed_meta__. "
            "Did you forget `__seed_meta__ = SeedMeta(...)`?"
        )

    filename = _get_code_seed_filename(cls)
    version = _get_code_seed_version(cls, db_name)
    checksum = _compute_code_seed_checksum(cls)

    logger = get_logger(db_name=db_name)
    description = meta.description or cls.__name__

    console.print(f"  Applying code seed {version}: {description}")

    if dry_run:
        console.print(f"    [yellow]Would apply code seed {version}: {description}[/yellow]")
        return

    from dbwarden.database.connection import get_db_connection

    if not hasattr(cls, "model"):
        raise SeedError(f"Seed class {cls.__name__} must have a 'model' attribute")

    model_cls = cls.model
    table_name = model_cls.__tablename__
    model_meta = getattr(model_cls, "Meta", None)
    schema = None
    if model_meta is not None:
        schema = getattr(model_meta, "pg_schema", None)
        if schema is None:
            backend_table = getattr(model_meta, "backend_table", None)
            if backend_table is not None:
                schema = getattr(backend_table, "schema", None)
    if schema is None:
        schema = getattr(model_cls.__table__, "schema", None)
    if schema:
        table_name = f"{schema}.{table_name}"
    on_conflict = meta.on_conflict

    with get_db_connection(db_name) as connection:
        if hasattr(cls, "generate"):
            generate = getattr(cls, "generate")
            session = SASession(bind=connection)
            generate(connection, session)
        elif hasattr(cls, "rows") and cls.rows is not None:
            for row in cls.rows:
                data = _row_to_dict(row, model_cls)
                if on_conflict == "ignore":
                    _insert_or_ignore(connection, table_name, data, meta.conflict_columns)
                elif on_conflict == "update":
                    _insert_or_update(connection, table_name, data, meta.conflict_columns)
                elif on_conflict == "error":
                    _validate_no_conflict(connection, table_name, data, meta.conflict_columns)
                    cols = ", ".join(data.keys())
                    placeholders = ", ".join(f":{k}" for k in data)
                    stmt = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                    connection.execute(text(stmt), data)
        else:
            raise SeedError(
                f"Seed class {cls.__name__} must define either `rows` or `generate()`"
            )

    record_applied_seed(
        version=version,
        description=description,
        filename=filename,
        seed_type="code",
        checksum=checksum,
        db_name=db_name,
    )

    logger.info(f"Applied code seed {version}: {description}")


def _validate_no_conflict(
    conn: Any, table: str, data: dict, conflict_columns: list[str] | None = None
) -> None:
    if not conflict_columns:
        return
    where = " AND ".join(f"{c} = :{c}" for c in conflict_columns)
    check_data = {c: data[c] for c in conflict_columns if c in data}
    if not check_data:
        return
    result = conn.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), check_data
    )
    count = result.scalar()
    if count and count > 0:
        raise SeedError(
            f"Row with {conflict_columns}={check_data} already exists in {table} "
            f"(on_conflict='error')"
        )


def get_pending_code_seeds(db_name: str | None = None) -> list[type[Seed]]:
    code_seeds = discover_code_seeds(db_name)
    applied_versions = get_applied_seed_versions(db_name)
    pending = []
    for cls in code_seeds:
        version = _get_code_seed_version(cls, db_name)
        if version not in applied_versions:
            pending.append(cls)
    pending.sort(key=lambda c: f"{c.__module__}.{c.__qualname__}")
    return pending


def rollback_code_seed(
    version: str,
    db_name: str | None = None,
) -> None:
    logger = get_logger(db_name=db_name)
    remove_seed_record(version, db_name=db_name)
    logger.info(f"Rolled back code seed record {version}")
