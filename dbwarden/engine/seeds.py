from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
import re
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session as SASession

from dbwarden.engine.checksum import calculate_checksum
from dbwarden.logging import get_logger
from dbwarden.output import console
from dbwarden.repositories.seeds_repo import (
    create_seeds_table_if_not_exists,
    get_applied_seed_versions,
    record_applied_seed,
    remove_seed_record,
)

SEED_SQL_PATTERN = re.compile(r"^V(\d{4})__(.+)\.sql$")
SEED_PYTHON_PATTERN = re.compile(r"^V(\d{4})__(.+)\.py$")


SQL_SEED_TEMPLATE = """-- {description}

INSERT INTO your_table (column1, column2)
VALUES ('value1', 'value2');
"""


PYTHON_SEED_TEMPLATE = '''"""Seed: {description}"""

def seed(connection, session):
    """Run seed data.

    Args:
        connection: SQLAlchemy raw DB-API connection.
        session: SQLAlchemy ORM Session.
    """
    # Use session for ORM access:
    # session.add(MyModel(...))
    # session.flush()

    # Or use connection for raw SQL:
    # connection.execute("INSERT INTO ...")
    pass
'''


def get_next_seed_number(seeds_dir: str) -> str:
    existing = _get_seed_filepaths_by_version(seeds_dir)
    if not existing:
        return "0001"
    existing_numbers = []
    for version in existing.keys():
        if version.isdigit():
            existing_numbers.append(int(version))
    if existing_numbers:
        next_num = max(existing_numbers) + 1
    else:
        next_num = 1
    return f"{next_num:04d}"


def generate_seed_filename(db_name: str, description: str, version: str, seed_type: str = "sql") -> str:
    safe_desc = re.sub(r"[^a-zA-Z0-9_]", "_", description.lower())
    safe_desc = re.sub(r"_+", "_", safe_desc)
    safe_desc = safe_desc.strip("_")
    ext = "sql" if seed_type == "sql" else "py"
    return f"V{version}__{safe_desc}.{ext}"


def _get_seed_filepaths_by_version(seeds_dir: str) -> dict[str, tuple[str, str]]:
    """Get seed file paths grouped by version.

    Returns:
        dict[str, tuple[str, str]]: Mapping of version to (filepath, seed_type).
    """
    seeds: dict[str, tuple[str, str]] = {}
    if not os.path.exists(seeds_dir):
        return seeds
    for filename in sorted(os.listdir(seeds_dir)):
        match = SEED_SQL_PATTERN.match(filename)
        if match:
            version = match.group(1)
            filepath = os.path.join(seeds_dir, filename)
            seeds[version] = (filepath, "sql")
            continue
        match = SEED_PYTHON_PATTERN.match(filename)
        if match:
            version = match.group(1)
            filepath = os.path.join(seeds_dir, filename)
            seeds[version] = (filepath, "python")
    return seeds


def get_pending_seeds(
    seeds_dir: str, db_name: str | None = None
) -> dict[str, tuple[str, str]]:
    all_seeds = _get_seed_filepaths_by_version(seeds_dir)
    if not all_seeds:
        return {}
    applied = get_applied_seed_versions(db_name)
    return {v: info for v, info in all_seeds.items() if v not in applied}


def get_seeds_to_rollback(
    seeds_dir: str, count: int | None = None, to_version: str | None = None, db_name: str | None = None
) -> dict[str, tuple[str, str]]:
    all_seeds = _get_seed_filepaths_by_version(seeds_dir)
    if not all_seeds:
        return {}
    applied = get_applied_seed_versions(db_name)
    applied_in_order = [v for v in sorted(all_seeds.keys()) if v in applied]
    if count is not None:
        target = applied_in_order[-count:] if count > 0 else []
    elif to_version is not None:
        target = [v for v in applied_in_order if v >= to_version]
    else:
        target = applied_in_order[-1:] if applied_in_order else []
    return {v: all_seeds[v] for v in target if v in all_seeds}


def read_sql_seed(filepath: str) -> str:
    with open(filepath, "r") as f:
        content = f.read()
    return content.strip()


def load_python_seed(filepath: str):
    module_name = Path(filepath).stem
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load seed module: {filepath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "seed"):
        raise AttributeError(
            f"Python seed file '{filepath}' must define a 'seed' function. "
            f"Expected: def seed(connection, session): ..."
        )
    fn = module.seed
    if not callable(fn):
        raise TypeError(f"'seed' in '{filepath}' is not callable")
    sig = inspect.signature(fn)
    required = [
        p.name
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty and p.name not in ("self", "cls")
    ]
    if len(required) < 2:
        raise TypeError(
            f"seed() in '{filepath}' must accept at least 2 arguments "
            f"(connection, session). Got signature: {sig}"
        )
    return fn


def apply_single_seed(
    version: str,
    filepath: str,
    seed_type: str,
    db_name: str | None = None,
    dry_run: bool = False,
) -> None:
    logger = get_logger(db_name=db_name)
    filename = Path(filepath).name
    description = _description_from_filename(filename)
    checksum = _compute_checksum(filepath, seed_type)

    console.print(f"  Applying seed V{version}: {filename}")

    if dry_run:
        console.print(f"    [yellow]Would apply seed V{version}: {filename}[/yellow]")
        return

    from dbwarden.database.connection import get_db_connection

    with get_db_connection(db_name) as connection:
        if seed_type == "sql":
            sql_content = read_sql_seed(filepath)
            statements = [s.strip() for s in sql_content.split(";") if s.strip()]
            for statement in statements:
                connection.execute(text(statement))
        elif seed_type == "python":
            seed_fn = load_python_seed(filepath)
            session = SASession(bind=connection)
            seed_fn(connection, session)
        else:
            raise ValueError(f"Unsupported seed_type: {seed_type}")

    record_applied_seed(
        version=version,
        description=description,
        filename=filename,
        seed_type=seed_type,
        checksum=checksum,
        db_name=db_name,
    )

    logger.info(f"Applied seed V{version}: {filename}")


def rollback_single_seed(
    version: str,
    db_name: str | None = None,
) -> None:
    logger = get_logger(db_name=db_name)
    remove_seed_record(version, db_name=db_name)
    logger.info(f"Rolled back seed record V{version}")


def _description_from_filename(filename: str) -> str:
    name = filename.replace(".sql", "").replace(".py", "")
    if name.startswith("V") and "__" in name:
        parts = name.split("__", 1)
        return parts[1].replace("_", " ").strip()
    return name.replace("_", " ").strip()


def _compute_checksum(filepath: str, seed_type: str) -> str:
    if seed_type == "sql":
        content = read_sql_seed(filepath)
        statements = [s.strip() for s in content.split(";") if s.strip()]
        return calculate_checksum(statements)
    else:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
