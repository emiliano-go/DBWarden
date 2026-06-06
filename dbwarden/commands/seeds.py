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
from dbwarden.output import console


def seed_create_cmd(
    description: str,
    seed_type: str = "sql",
    database: str | None = None,
    verbose: bool = False,
) -> None:
    """Create a new seed file."""
    logger = get_logger(verbose=verbose)
    config = get_database(database)
    multi_config = get_multi_db_config()
    db_name = database or multi_config.default

    seeds_dir = Path.cwd() / SEEDS_DIR
    if not seeds_dir.exists():
        seeds_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created seeds directory: {seeds_dir}")
        console.print(f"Created seeds directory: {seeds_dir}", style="green")

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
    console.print(f"Created seed file: {filepath}", style="green")


def seed_apply_cmd(
    version: str | None = None,
    dry_run: bool = False,
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    """Apply pending seeds."""
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
                console.print(f"Error seeding database '{db_name}': {e}", style="bold red")
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
            console.print(f"Seed V{version} not found in seeds directory.", style="red")
            return
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
        console.print("All seeds are up to date.", style="cyan")
        return

    console.print(f"Applying {len(pending)} pending seed(s)...", style="bold cyan")
    for ver, (fp, stype) in sorted(pending.items()):
        apply_single_seed(
            version=ver,
            filepath=fp,
            seed_type=stype,
            db_name=db_name,
            dry_run=dry_run,
        )

    if not dry_run:
        console.print(f"Seeds applied successfully: {len(pending)} seed(s).", style="green")
        if metrics_enabled():
            latest = max(pending.keys())
            set_seed_version(db_name, latest)
    else:
        console.print(f"Dry-run: {len(pending)} seed(s) would be applied.", style="yellow")


def seed_list_cmd(
    database: str | None = None,
    all_databases: bool = False,
    verbose: bool = False,
) -> None:
    """List seeds and their applied status."""
    from dbwarden.repositories.seeds_repo import get_all_seed_records, get_seeds_directory

    if all_databases:
        config = get_multi_db_config()
        for db_name in config.databases:
            console.print(f"\n=== Seeds for database: {db_name} ===", style="bold cyan")
            try:
                _list_seeds_single(db_name, verbose)
            except DirectoryNotFoundError:
                console.print("  No seeds directory.", style="yellow")
    else:
        db_name = database or get_multi_db_config().default
        console.print(f"\n=== Seeds for database: {db_name} ===", style="bold cyan")
        try:
            _list_seeds_single(db_name, verbose)
        except DirectoryNotFoundError:
            console.print("  No seeds directory.", style="yellow")


def _list_seeds_single(db_name: str | None = None, verbose: bool = False) -> None:
    from dbwarden.repositories.seeds_repo import get_all_seed_records, get_seeds_directory

    seeds_dir = get_seeds_directory(db_name)
    all_seeds = _get_seed_filepaths_by_version(seeds_dir)
    if not all_seeds:
        console.print("  No seed files found.", style="yellow")
        return

    applied = get_all_seed_records(db_name)
    applied_versions = {r.version for r in applied}

    for version in sorted(all_seeds.keys()):
        fp, stype = all_seeds[version]
        filename = Path(fp).name
        status = "applied" if version in applied_versions else "pending"
        color = "green" if status == "applied" else "white"
        console.print(f"  V{version} [{status}] {filename}", style=color)


def seed_rollback_cmd(
    count: int | None = None,
    to_version: str | None = None,
    database: str | None = None,
    verbose: bool = False,
) -> None:
    """Rollback seed tracking records."""
    logger = get_logger(verbose=verbose, db_name=database)

    if count is not None and to_version is not None:
        raise ValueError("Cannot specify both 'count' and 'to-version'.")

    if count is None and to_version is None:
        count = 1

    from dbwarden.repositories.seeds_repo import get_seeds_directory

    try:
        seeds_dir = get_seeds_directory(database)
    except DirectoryNotFoundError:
        console.print("No seeds directory found. Nothing to rollback.", style="cyan")
        return

    to_rollback = get_seeds_to_rollback(
        seeds_dir, count=count, to_version=to_version, db_name=database
    )

    if not to_rollback:
        console.print("Nothing to rollback.", style="cyan")
        return

    for version in sorted(to_rollback.keys(), reverse=True):
        rollback_single_seed(version, db_name=database)

    console.print(
        f"Rollback completed: {len(to_rollback)} seed record(s) removed.",
        style="green",
    )
