from typing import Final

MIGRATIONS_DIR: Final[str] = "migrations"
ENV_FILE: Final[str] = ".env"
TOML_FILE: Final[str] = "warden.toml"
RUNS_ALWAYS_FILE_PREFIX: Final[str] = "RA__"
RUNS_ON_CHANGE_FILE_PREFIX: Final[str] = "ROC__"
VERSION_FILE_PREFIX: Final[str] = "V"
DEFAULT_DELIMITER: Final[str] = ";"

DBWARDEN_VERSION: Final[str] = "1.0.0"

LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
