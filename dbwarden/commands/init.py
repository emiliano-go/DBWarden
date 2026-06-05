from pathlib import Path
import os
import tempfile

from dbwarden.constants import MIGRATIONS_DIR
from dbwarden.logging import get_logger
from dbwarden.output import console


def _atomic_write(path: Path, content: str) -> None:
    """Write content atomically using rename."""
    path = path.resolve()
    dir_path = path.parent
    
    # Create temp file in same directory for atomic rename
    fd, tmp_path = tempfile.mkstemp(
        dir=str(dir_path),
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Backup existing file
        if path.exists():
            backup_path = path.with_suffix(path.suffix + ".bak")
            path.replace(backup_path)
        
        # Atomic rename from temp to final
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _ensure_settings_file(settings_path: Path, db_name: str) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    content = ""
    if settings_path.exists():
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
            '    database_url_sync="sqlite:///./app.db",\n'
            f'    migrations_dir="migrations/{db_name}",\n'
            ")\n"
        )
        updated = f"{updated.rstrip()}{scaffold}"

    if updated != content:
        _atomic_write(settings_path, updated)


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
