import tomllib
from pathlib import Path

from dbwarden.config import get_toml_path
from dbwarden.constants import DBWARDEN_VERSION


def config_cmd() -> None:
    """Display current warden.toml configuration."""
    toml_path = get_toml_path()

    if not toml_path:
        print("No warden.toml found.")
        return

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    warden_config = config.get("warden", config)

    print(f"DBWarden Configuration ({toml_path}):")
    print("=" * 50)

    if "sqlalchemy_url" in warden_config:
        url = warden_config["sqlalchemy_url"]
        if url:
            masked_url = _mask_password(url)
            print(f"sqlalchemy_url: {masked_url}")

    if "model_paths" in warden_config:
        model_paths = warden_config["model_paths"]
        if model_paths:
            print(f"model_paths: {model_paths}")

    if "postgres_schema" in warden_config:
        schema = warden_config["postgres_schema"]
        if schema:
            print(f"postgres_schema: {schema}")

    print()
    print(f"Config file: {toml_path}")


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
    print(DBWARDEN_VERSION)
