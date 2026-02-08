from pathlib import Path

from dbwarden.constants import MIGRATIONS_DIR
from dbwarden.logging import get_logger


def init_cmd() -> None:
    """
    Initialize DBWarden in current directory.

    Creates only the migrations directory without touching the database.
    """
    logger = get_logger()
    migrations_dir = Path(MIGRATIONS_DIR)
    migrations_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Initialized DBWarden migrations directory: {migrations_dir.absolute()}"
    )
    print(f"DBWarden migrations directory created: {migrations_dir.absolute()}")
    print("\nNext steps:")
    print("  1. Create a .env file with STRATA_SQLALCHEMY_URL")
    print("  2. Run 'dbwarden make-migrations' to generate migrations from your models")
