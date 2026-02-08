from pathlib import Path

from strata.constants import MIGRATIONS_DIR
from strata.exceptions import DirectoryNotFoundError


def validate_strata_directory() -> None:
    """
    Ensure command is run from a project directory with migrations/ folder.

    Raises:
        DirectoryNotFoundError: If no valid migrations directory is found.
    """
    current_dir = Path.cwd()

    migrations_dir = current_dir / MIGRATIONS_DIR
    if migrations_dir.exists() and migrations_dir.is_dir():
        return

    raise DirectoryNotFoundError(
        "migrations directory not found. Please run 'strata init' first."
    )
