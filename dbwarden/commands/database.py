import tomllib
from pathlib import Path

from dbwarden.constants import TOML_FILE
from dbwarden.config import get_multi_db_config, list_databases
from dbwarden.logging import get_logger


def _write_toml(path: Path, data: dict) -> None:
    """Write TOML data to file."""
    try:
        import tomli_w

        with open(path, "wb") as f:
            tomli_w.dump(data, f)
    except ImportError:
        import json

        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def handle_database_list() -> None:
    """Handle the database list command."""
    logger = get_logger()
    config = get_multi_db_config()

    print("Databases:")
    for name, db_config in config.databases.items():
        is_default = " (default)" if name == config.default else ""
        url = db_config.sqlalchemy_url
        if "://" in url:
            parts = url.split("://", 1)
            if "@" in parts[1]:
                auth, rest = parts[1].split("@", 1)
                if ":" in auth:
                    user, _ = auth.split(":", 1)
                    url = f"{parts[0]}://{user}:***@{rest}"
        print(f"  {name}{is_default} - {url}")
        print(f"    migrations: {db_config.migrations_dir}")


def handle_database_add(
    name: str,
    url: str,
    model_paths: list[str] | None = None,
    migrations_dir: str | None = None,
    default: bool = False,
) -> None:
    """Handle the database add command."""
    logger = get_logger()
    current_dir = Path.cwd()
    toml_path = current_dir / TOML_FILE

    if not toml_path.exists():
        raise FileNotFoundError(
            f"warden.toml not found in {current_dir}. Run 'dbwarden init' first."
        )

    with open(toml_path, "rb") as f:
        config_data = tomllib.load(f)

    if "warden" in config_data:
        warden = config_data["warden"]
    else:
        warden = config_data

    database_section = warden.get("database", {})

    if name in database_section:
        raise ValueError(f"Database '{name}' already exists in warden.toml")

    db_config = {
        "sqlalchemy_url": url,
    }

    if model_paths:
        db_config["model_paths"] = model_paths

    if migrations_dir:
        db_config["migrations_dir"] = migrations_dir
    else:
        db_config["migrations_dir"] = f"migrations/{name}"
        Path(current_dir / db_config["migrations_dir"]).mkdir(
            parents=True, exist_ok=True
        )

    database_section[name] = db_config
    warden["database"] = database_section

    if default or "default" not in warden:
        warden["default"] = name

    if "warden" in config_data:
        config_data["warden"] = warden
    else:
        config_data = warden

    _write_toml(toml_path, config_data)

    logger.info(f"Added database '{name}' to warden.toml")
    print(f"Added database '{name}' to warden.toml")
    print(f"  URL: {url}")
    print(f"  Migrations: {db_config['migrations_dir']}")
    if default:
        print(f"  Set as default database")


def handle_database_remove(name: str, force: bool = False) -> None:
    """Handle the database remove command."""
    logger = get_logger()
    current_dir = Path.cwd()
    toml_path = current_dir / TOML_FILE

    if not toml_path.exists():
        raise FileNotFoundError(
            f"warden.toml not found in {current_dir}. Run 'dbwarden init' first."
        )

    config = get_multi_db_config()

    if name not in config.databases:
        raise ValueError(f"Database '{name}' not found in warden.toml")

    if len(config.databases) == 1:
        raise ValueError(
            "Cannot remove the last database. At least one database is required."
        )

    if name == config.default and not force:
        raise ValueError(
            f"Cannot remove default database '{name}' without --force flag."
        )

    with open(toml_path, "rb") as f:
        config_data = tomllib.load(f)

    if "warden" in config_data:
        warden = config_data["warden"]
    else:
        warden = config_data

    database_section = warden.get("database", {})

    del database_section[name]
    warden["database"] = database_section

    if warden.get("default") == name:
        remaining = list(database_section.keys())
        warden["default"] = remaining[0] if remaining else "default"

    if "warden" in config_data:
        config_data["warden"] = warden
    else:
        config_data = warden

    _write_toml(toml_path, config_data)

    logger.info(f"Removed database '{name}' from warden.toml")
    print(f"Removed database '{name}' from warden.toml")
