from dbwarden.config import display_value, get_multi_db_config
from dbwarden.constants import DBWARDEN_VERSION
from dbwarden.output import console


def config_cmd() -> None:
    """Display current DBWarden configuration."""
    config = get_multi_db_config()

    console.print("DBWarden Configuration:", style="bold cyan")
    console.print("=" * 50, style="dim")

    console.print(f"default: {config.default}", style="green")
    console.print("databases:", style="bold white")
    for name, db in config.databases.items():
        marker = " (default)" if name == config.default else ""
        database_url = display_value(
            db,
            "database_url_sync",
            _mask_password(db.sqlalchemy_url),
        )
        console.print(f"  - {name}{marker}", style="cyan")
        console.print(
            f"    database_type: {display_value(db, 'database_type', db.database_type)}",
            style="white",
        )
        console.print(
            f"    database_url_sync: {database_url}",
            style="white",
            markup=False,
            highlight=False,
        )
        console.print(
            f"    migrations_dir: {display_value(db, 'migrations_dir', db.migrations_dir)}",
            style="white",
        )
        console.print(
            f"    migration_table: {display_value(db, 'migration_table', db.migration_table)}",
            style="white",
        )
        console.print(
            f"    seed_table: {display_value(db, 'seed_table', db.seed_table)}",
            style="white",
        )
        if db.model_paths:
            console.print(
                f"    model_paths: {display_value(db, 'model_paths', db.model_paths)}",
                style="white",
            )
        if db.dev_database_url:
            dev_database_url = display_value(
                db,
                "dev_database_url",
                _mask_password(db.dev_database_url),
            )
            console.print(
                f"    dev_database_url: {dev_database_url}",
                style="white",
                markup=False,
                highlight=False,
            )
        if db.dev_database_type:
            console.print(
                f"    dev_database_type: {display_value(db, 'dev_database_type', db.dev_database_type)}",
                style="white",
            )

    console.print()
    console.print("Config source: python settings", style="dim")


def _mask_password(url: str) -> str:
    """Mask password in connection URL."""
    if "@" in url:
        try:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                creds, host_part = rest.split("@", 1)
                if ":" in creds:
                    user, _ = creds.split(":", 1)
                    return f"{protocol}://{user}:***@{host_part}"
        except Exception:
            pass
    return url


def version_cmd() -> None:
    """Display DBWarden version."""
    console.print(DBWARDEN_VERSION, style="bold green")
