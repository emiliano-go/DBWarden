from pathlib import Path

from dbwarden.constants import MIGRATIONS_DIR, TOML_FILE
from dbwarden.logging import get_logger


def init_cmd(database: str | None = None) -> None:
    """
    Initialize DBWarden in current directory.

    Creates the migrations directory and a warden.toml config file.

    Args:
        database: Optional database name to create a specific migration directory.
    """
    logger = get_logger()
    current_dir = Path.cwd()

    migrations_dir = current_dir / MIGRATIONS_DIR
    migrations_dir.mkdir(parents=True, exist_ok=True)

    toml_path = current_dir / TOML_FILE
    if not toml_path.exists():
        db_name = database or "default"
        db_migrations_dir = migrations_dir / db_name
        db_migrations_dir.mkdir(parents=True, exist_ok=True)
        toml_content = f"""# DBWarden Configuration
# See documentation: https://emiliano-gandini-outeda.me/DBWarden/

# Default database
default = "{db_name}"

# Database configurations
[database]
[database.{db_name}]
# Database connection URL (required)
sqlalchemy_url = "sqlite:///./development.db"

# PostgreSQL schema (optional)
# postgres_schema = "public"

# Paths to SQLAlchemy models for auto-migration (optional)
# model_paths = ["app/models/"]

# Migration directory (optional, defaults to "migrations/<name>")
# migrations_dir = "migrations/{db_name}"
"""
        toml_path.write_text(toml_content)
        logger.info(f"Created configuration file: {toml_path}")
        print(f"Created configuration file: {toml_path}")
        logger.info(
            f"Initialized DBWarden migrations directory: {db_migrations_dir.absolute()}"
        )
        print(f"DBWarden migrations directory created: {db_migrations_dir.absolute()}")
    else:
        db_name = database
        if db_name:
            db_migrations_dir = migrations_dir / db_name
            db_migrations_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Initialized DBWarden migrations directory for '{db_name}': {db_migrations_dir.absolute()}"
            )
            print(
                f"DBWarden migrations directory created: {db_migrations_dir.absolute()}"
            )
        else:
            logger.info(
                f"Initialized DBWarden migrations directory: {migrations_dir.absolute()}"
            )
            print(f"DBWarden migrations directory created: {migrations_dir.absolute()}")

    print("\nNext steps:")
    print("  1. Edit warden.toml with your database connection URLs")
    print("  2. Run 'dbwarden make-migrations -d <name>' to generate migrations")
