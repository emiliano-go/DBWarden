from importlib.metadata import version
from typing import Final

MIGRATIONS_DIR: Final[str] = "migrations"
TOML_FILE: Final[str] = "warden.toml"
RUNS_ALWAYS_FILE_PREFIX: Final[str] = "RA__"
RUNS_ON_CHANGE_FILE_PREFIX: Final[str] = "ROC__"
VERSION_FILE_PREFIX: Final[str] = "V"
DEFAULT_DELIMITER: Final[str] = ";"

DBWARDEN_VERSION: Final[str] = version("dbwarden")

LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
