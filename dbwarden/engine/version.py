from dbwarden.constants import (
    MIGRATIONS_DIR,
    RUNS_ALWAYS_FILE_PREFIX,
    RUNS_ON_CHANGE_FILE_PREFIX,
)
from dbwarden.exceptions import DirectoryNotFoundError
from pathlib import Path
import re
import os
from typing import Optional


def get_migrations_directory() -> str:
    """
    Get the migrations directory path.

    Returns:
        str: Path to migrations directory.

    Raises:
        DirectoryNotFoundError: If migrations directory is not found.
    """
    current_dir = Path.cwd()
    migrations_dir = current_dir / MIGRATIONS_DIR

    if not migrations_dir.exists() or not migrations_dir.is_dir():
        raise DirectoryNotFoundError(
            f"migrations directory not found. Please run 'dbwarden init' first."
        )
    return str(migrations_dir)


MIGRATION_PATTERN = re.compile(r"^(\d{4})_(.+)\.sql$")
RUNS_ALWAYS_PATTERN = re.compile(rf"^{re.escape(RUNS_ALWAYS_FILE_PREFIX)}(.+)\.sql$")
RUNS_ON_CHANGE_PATTERN = re.compile(
    rf"^{re.escape(RUNS_ON_CHANGE_FILE_PREFIX)}(.+)\.sql$"
)


def get_migration_filepaths_by_version(
    directory: str,
    version_to_start_from: Optional[str] = None,
    end_version: Optional[str] = None,
) -> dict[str, str]:
    """
    Get migration file paths grouped by version.

    Args:
        directory: Path to migrations directory.
        version_to_start_from: Only get migrations after this version.
        end_version: Only get migrations up to this version.

    Returns:
        dict[str, str]: Mapping of version to file path.
    """
    migrations: dict[str, str] = {}

    if not os.path.exists(directory):
        return {}

    for filename in sorted(os.listdir(directory)):
        match = MIGRATION_PATTERN.match(filename)
        if match:
            version = match.group(1)
            filepath = os.path.join(directory, filename)
            migrations[version] = filepath

    if version_to_start_from:
        versions = list(migrations.keys())
        start_idx = (
            versions.index(version_to_start_from) + 1
            if version_to_start_from in versions
            else 0
        )
        migrations = {k: v for k, v in list(migrations.items())[start_idx:]}

    if end_version:
        versions = list(migrations.keys())
        if end_version in versions:
            end_idx = versions.index(end_version)
            migrations = {k: v for k, v in list(migrations.items())[: end_idx + 1]}

    return migrations


def get_runs_always_filepaths(directory: str) -> list[str]:
    """
    Get all runs-always (RA__) migration file paths.

    Args:
        directory: Path to migrations directory.

    Returns:
        list[str]: List of file paths for runs-always migrations.
    """
    filepaths = []

    if not os.path.exists(directory):
        return []

    for filename in sorted(os.listdir(directory)):
        match = RUNS_ALWAYS_PATTERN.match(filename)
        if match:
            filepath = os.path.join(directory, filename)
            filepaths.append(filepath)

    return filepaths


def get_runs_on_change_filepaths(
    directory: str, changed_only: bool = False
) -> list[str]:
    """
    Get all runs-on-change (ROC__) migration file paths.

    Args:
        directory: Path to migrations directory.
        changed_only: Only return files that have changed since last run.

    Returns:
        list[str]: List of file paths for runs-on-change migrations.
    """
    from dbwarden.engine.checksum import calculate_checksum
    from dbwarden.repositories import (
        get_existing_runs_on_change_filenames_to_checksums,
    )

    filepaths = []

    if not os.path.exists(directory):
        return []

    for filename in sorted(os.listdir(directory)):
        match = RUNS_ON_CHANGE_PATTERN.match(filename)
        if match:
            filepath = os.path.join(directory, filename)
            if changed_only:
                existing_checksums = (
                    get_existing_runs_on_change_filenames_to_checksums()
                )
                if filename in existing_checksums:
                    with open(filepath, "r") as f:
                        content = f.read()
                    from dbwarden.engine.file_parser import parse_upgrade_statements

                    statements = parse_upgrade_statements(filepath)
                    current_checksum = calculate_checksum(statements)
                    existing_checksum = existing_checksums[filename]
                    if current_checksum != existing_checksum:
                        filepaths.append(filepath)
                else:
                    filepaths.append(filepath)
            else:
                filepaths.append(filepath)

    return filepaths


def get_all_repeatable_filepaths(directory: str) -> dict[str, list[str]]:
    """
    Get all repeatable migration file paths (both RA__ and ROC__).

    Args:
        directory: Path to migrations directory.

    Returns:
        dict[str, list[str]]: Dictionary with 'runs_always' and 'runs_on_change' keys.
    """
    return {
        "runs_always": get_runs_always_filepaths(directory),
        "runs_on_change": get_runs_on_change_filepaths(directory),
    }


def get_next_migration_number(directory: str) -> str:
    """
    Get the next migration number for a new migration.

    Args:
        directory: Path to migrations directory.

    Returns:
        str: Next migration number as 4-digit string.
    """
    existing_migrations = get_migration_filepaths_by_version(directory)
    if not existing_migrations:
        return "0001"

    existing_numbers = []
    for version in existing_migrations.keys():
        if version.isdigit():
            existing_numbers.append(int(version))

    if existing_numbers:
        next_num = max(existing_numbers) + 1
    else:
        next_num = 1

    return f"{next_num:04d}"


def get_all_migrations_with_metadata(
    directory: str,
) -> list[tuple[str, str, list[str], bool]]:
    """
    Get all migration files with their metadata.

    Returns:
        list[tuple]: [(version, filepath, depends_on, is_seed), ...]
    """
    from dbwarden.engine.file_parser import parse_migration_header

    migrations: list[tuple[str, str, list[str], bool]] = []

    if not os.path.exists(directory):
        return []

    for filename in sorted(os.listdir(directory)):
        match = MIGRATION_PATTERN.match(filename)
        if match:
            version = match.group(1)
            filepath = os.path.join(directory, filename)
            metadata = parse_migration_header(filepath)
            migrations.append(
                (version, filepath, metadata.depends_on, metadata.is_seed)
            )

    return migrations


def resolve_migration_order(
    directory: str, applied_versions: set[str]
) -> list[tuple[str, str, list[str], bool]]:
    """
    Resolve migration order based on dependencies.

    Args:
        directory: Path to migrations directory.
        applied_versions: Set of already applied migration versions.

    Returns:
        list[tuple]: [(version, filepath, depends_on, is_seed), ...] in execution order.
    """
    all_migrations = get_all_migrations_with_metadata(directory)

    pending = [
        (v, fp, deps, seed)
        for v, fp, deps, seed in all_migrations
        if v not in applied_versions
    ]

    resolved: list[tuple[str, str, list[str], bool]] = []
    remaining = pending.copy()
    iterations = 0
    max_iterations = len(pending) * 2

    while remaining and iterations < max_iterations:
        iterations += 1
        for migration in remaining[:]:
            version, filepath, deps, seed = migration
            deps_met = all(
                d in applied_versions or d in [m[0] for m in resolved] for d in deps
            )
            if deps_met:
                resolved.append(migration)
                remaining.remove(migration)

    if remaining:
        unresolved_versions = [m[0] for m in remaining]
        raise ValueError(
            f"Cannot resolve migration dependencies. Unresolved migrations: {unresolved_versions}. "
            f"Missing dependencies for: {[m[0] for m in remaining if not all(d in applied_versions or d in [mm[0] for mm in resolved] for d in m[2])]}"
        )

    return resolved


def parse_version_string(version: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers."""
    return tuple(int(x) for x in version.split("."))


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    p1 = parse_version_string(v1)
    p2 = parse_version_string(v2)

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0
