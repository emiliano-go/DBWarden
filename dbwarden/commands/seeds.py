from __future__ import annotations

import os
from pathlib import Path

from dbwarden.config import get_database, get_multi_db_config
from dbwarden.constants import SEEDS_DIR
from dbwarden.engine.seeds import (
    SQL_SEED_TEMPLATE,
    PYTHON_SEED_TEMPLATE,
    _get_seed_filepaths_by_version,
    apply_single_seed,
    generate_seed_filename,
    get_next_seed_number,
    get_pending_seeds,
    get_seeds_to_rollback,
    rollback_single_seed,
)
from dbwarden.exceptions import DirectoryNotFoundError, NoSeedsError
from dbwarden.logging import get_logger
from dbwarden.metrics import metrics_enabled, set_seed_version
from dbwarden.output import data_table, error, info, render, section, success, warning


def seed_create_cmd(
    description: str,
    seed_type: str = "sql",
    database: str | None = None,
    verbose: bool = False,
) -> None:
    """Create a new seed file."""
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_create"):
        HookRegistry.execute_single(
            "seed_create",
            description,
            seed_type=seed_type,
            database=database,
            verbose=verbose,
        )
        return

    logger = get_logger(verbose=verbose)
    config = get_database(database)
    multi_config = get_multi_db_config()
    db_name = database or multi_config.default

    seeds_dir = Path.cwd() / SEEDS_DIR
    if not seeds_dir.exists():
        seeds_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created seeds directory: {seeds_dir}")
        success(f"Created seeds directory: {seeds_dir}")

    version = get_next_seed_number(str(seeds_dir))
    filename = generate_seed_filename(db_name, description, version, seed_type)
    filepath = seeds_dir / filename

    if seed_type == "sql":
        template = f"-- {description}\n\n{SQL_SEED_TEMPLATE.replace('-- {description}', '').strip()}\n"
    else:
        template = PYTHON_SEED_TEMPLATE.format(description=description)

    with open(filepath, "w") as f:
        f.write(template)

    logger.info(f"Created seed file: {filename}")
    success(f"Created seed file: {filepath}")


def seed_apply_cmd(
    version: str | None = None,
    dry_run: bool = False,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    """Apply pending seeds."""
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_apply"):
        HookRegistry.execute_single(
            "seed_apply",
            version=version,
            dry_run=dry_run,
            database=database,
            all_databases=all_databases,
            verbose=verbose,
        )
        return

    if all_databases:
        config = get_multi_db_config()
        for db_name in config.databases:
            try:
                _apply_seeds_single(
                    db_name=db_name,
                    version=version,
                    dry_run=dry_run,
                    verbose=verbose,
                )
            except Exception as e:
                error(f"Error seeding database '{db_name}': {e}")
                continue
    else:
        _apply_seeds_single(
            db_name=database,
            version=version,
            dry_run=dry_run,
            verbose=verbose,
        )


def _apply_seeds_single(
    db_name: str | None = None,
    version: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    logger = get_logger(verbose=verbose, db_name=db_name)

    from dbwarden.repositories.seeds_repo import (
        create_seeds_table_if_not_exists,
        get_seeds_directory,
    )

    seeds_dir = get_seeds_directory(db_name)

    create_seeds_table_if_not_exists(db_name)

    if version is not None:
        all_seeds = _get_seed_filepaths_by_version(seeds_dir)
        if version not in all_seeds:
            error(f"Seed V{version} not found in seeds directory.")
            raise SystemExit(1)
        apply_single_seed(
            version=version,
            filepath=all_seeds[version][0],
            seed_type=all_seeds[version][1],
            db_name=db_name,
            dry_run=dry_run,
        )
        return

    pending = get_pending_seeds(seeds_dir, db_name=db_name)
    if not pending:
        info("All seeds are up to date.")
        return

    section(f"Applying {len(pending)} pending seed(s)")
    for ver, (fp, stype) in sorted(pending.items()):
        apply_single_seed(
            version=ver,
            filepath=fp,
            seed_type=stype,
            db_name=db_name,
            dry_run=dry_run,
        )

    if not dry_run:
        success(f"Seeds applied successfully: {len(pending)} seed(s).")
        if metrics_enabled():
            latest = max(pending.keys())
            set_seed_version(db_name, latest)
    else:
        warning(f"Dry-run: {len(pending)} seed(s) would be applied.")


def seed_list_cmd(
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
    prune: bool = False,
) -> None:
    """List seeds and their applied status."""
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_list"):
        HookRegistry.execute_single(
            "seed_list",
            database=database,
            all_databases=all_databases,
            verbose=verbose,
            prune=prune,
        )
        return

    from dbwarden.repositories.seeds_repo import (
        get_all_seed_records,
        get_seeds_directory,
        remove_seed_record,
    )

    if prune:
        _prune_orphaned_seeds(database, all_databases)

    if all_databases:
        config = get_multi_db_config()
        for db_name in config.databases:
            section(f"Seeds for database: {db_name}")
            try:
                _list_seeds_single(db_name, verbose)
            except DirectoryNotFoundError:
                warning("No seeds directory.")
    else:
        db_name = database or get_multi_db_config().default
        section(f"Seeds for database: {db_name}")
        try:
            _list_seeds_single(db_name, verbose)
        except DirectoryNotFoundError:
            warning("No seeds directory.")


def _list_seeds_single(db_name: str | None = None, verbose: bool = False) -> None:
    from dbwarden.repositories.seeds_repo import get_all_seed_records, get_seeds_directory

    seeds_dir = get_seeds_directory(db_name)
    all_seeds = _get_seed_filepaths_by_version(seeds_dir)
    if not all_seeds:
        warning("No seed files found.")
        return

    applied = get_all_seed_records(db_name)
    applied_versions = {r.version for r in applied}

    render(
        data_table(
            None,
            ("Version", "Status", "File"),
            (
                (
                    f"V{version}",
                    "applied" if version in applied_versions else "pending",
                    Path(all_seeds[version][0]).name,
                )
                for version in sorted(all_seeds.keys())
            ),
        )
    )


def seed_rollback_cmd(
    count: int | None = None,
    to_version: str | None = None,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    """Rollback seed tracking records."""
    from dbwarden.plugin import HookRegistry

    if HookRegistry.is_registered("seed_rollback"):
        HookRegistry.execute_single(
            "seed_rollback",
            count=count,
            to_version=to_version,
            database=database,
            all_databases=all_databases,
            verbose=verbose,
        )
        return

    if all_databases:
        config = get_multi_db_config()
        for db_name in config.databases:
            try:
                _rollback_seeds_single(
                    count=count,
                    to_version=to_version,
                    db_name=db_name,
                    verbose=verbose,
                )
            except Exception as e:
                error(f"Error rolling back seeds for database '{db_name}': {e}")
                continue
    else:
        _rollback_seeds_single(
            count=count,
            to_version=to_version,
            db_name=database,
            verbose=verbose,
        )


def _rollback_seeds_single(
    count: int | None = None,
    to_version: str | None = None,
    db_name: str | None = None,
    verbose: bool = False,
) -> None:
    """Rollback seed tracking records for a single database."""
    logger = get_logger(verbose=verbose, db_name=db_name)

    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to-version'.")

    if count is None and to_version is None:
        count = 1

    from dbwarden.repositories.seeds_repo import create_seeds_table_if_not_exists, get_seeds_directory

    create_seeds_table_if_not_exists(db_name)

    try:
        seeds_dir = get_seeds_directory(db_name)
    except DirectoryNotFoundError:
        info("No seeds directory found. Nothing to rollback.")
        return

    to_rollback = get_seeds_to_rollback(
        seeds_dir, count=count, to_version=to_version, db_name=db_name
    )

    if not to_rollback:
        info("Nothing to rollback.")
        return

    for version in sorted(to_rollback.keys(), reverse=True):
        rollback_single_seed(version, db_name=db_name)

    success(f"Rollback completed: {len(to_rollback)} seed record(s) removed.")


def _prune_orphaned_seeds(database: str | None = None, all_databases: bool = False) -> None:
    from dbwarden.repositories.seeds_repo import (
        get_all_seed_records,
        get_seeds_directory,
        remove_seed_record,
    )

    def _prune_single(db_name: str | None) -> None:
        try:
            seeds_dir = get_seeds_directory(db_name)
        except DirectoryNotFoundError:
            return
        on_disk = set()
        for f in Path(seeds_dir).iterdir():
            if f.suffix in (".sql", ".py") and f.name.startswith("V"):
                on_disk.add(f.name)
        records = get_all_seed_records(db_name)
        pruned = 0
        for rec in records:
            if rec.seed_type in ("sql", "python") and rec.filename not in on_disk:
                remove_seed_record(rec.version, db_name)
                warning(f"Removed orphaned record: V{rec.version} ({rec.filename})")
                pruned += 1
        if pruned:
            success(f"Pruned {pruned} orphaned seed record(s) for {db_name}.")
        else:
            info(f"No orphaned seed records for {db_name}.")

    if all_databases:
        config = get_multi_db_config()
        for db_name in config.databases:
            _prune_single(db_name)
    else:
        db_name = database or get_multi_db_config().default
        _prune_single(db_name)
