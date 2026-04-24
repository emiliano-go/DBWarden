from pathlib import Path

from dbwarden.constants import MIGRATIONS_DIR
from dbwarden.logging import get_logger
from dbwarden.output import console


def _ensure_settings_file(settings_path: Path, db_name: str) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings_path.exists():
        settings_path.write_text("", encoding="utf-8")

    content = settings_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    import_line = "from dbwarden import database_config"
    has_import = any(line.strip() == import_line for line in lines)
    has_scaffold = "database_config(" in content

    updated = content
    if not has_import:
        updated = (
            f"{import_line}\n\n{updated}" if updated.strip() else f"{import_line}\n"
        )

    if not has_scaffold:
        scaffold = (
            "\n\ndatabase_config(\n"
            f'    database_name="{db_name}",\n'
            "    default=True,\n"
            '    database_type="sqlite",\n'
            '    database_url="sqlite:///./app.db",\n'
            f'    migrations_dir="migrations/{db_name}",\n'
            ")\n"
        )
        updated = f"{updated.rstrip()}{scaffold}"

    if updated != content:
        settings_path.write_text(updated, encoding="utf-8")


def init_cmd(database: str | None = None) -> None:
    """
    Initialize DBWarden in current directory.

    Creates the migrations directory and a Python settings config scaffold.

    Args:
        database: Optional database name for scaffold defaults.
    """
    logger = get_logger()
    current_dir = Path.cwd()

    migrations_dir = current_dir / MIGRATIONS_DIR
    migrations_dir.mkdir(parents=True, exist_ok=True)

    db_name = database or "primary"
    db_migrations_dir = migrations_dir / db_name
    db_migrations_dir.mkdir(parents=True, exist_ok=True)

    settings_path = current_dir / "dbwarden.py"
    _ensure_settings_file(settings_path, db_name)

    logger.info(f"Created/updated configuration file: {settings_path}")
    console.print(f"Created/updated configuration file: {settings_path}", style="green")
    logger.info(
        f"Initialized DBWarden migrations directory: {db_migrations_dir.absolute()}"
    )
    console.print(
        f"DBWarden migrations directory created: {db_migrations_dir.absolute()}",
        style="green",
    )

    console.print("\nNext steps:", style="bold cyan")
    console.print("  1. Edit dbwarden.py with your database configuration", style="white")
    console.print(
        "  2. Run 'dbwarden make-migrations -d <name>' to generate migrations",
        style="white",
    )
