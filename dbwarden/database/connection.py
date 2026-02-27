import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from dbwarden.config import get_config
from dbwarden.logging import get_logger


@lru_cache(maxsize=1)
def _get_engine(url: str) -> Engine:
    return create_engine(url=url)


_connection_init_logged = False


def reset_connection_logging() -> None:
    """Reset the connection init logging flag for new CLI invocations."""
    global _connection_init_logged
    _connection_init_logged = False


@contextmanager
def get_db_connection() -> Generator[Any, None, None]:
    """
    Context manager that yields a database connection.
    """
    global _connection_init_logged
    logger = get_logger()
    config = get_config()

    engine = _get_engine(config.sqlalchemy_url)

    if not _connection_init_logged:
        logger.log_connection_init("sync")
        _connection_init_logged = True

    with engine.begin() as connection:
        postgres_schema = config.postgres_schema
        if postgres_schema:
            connection.execute(
                text("SET search_path TO :postgres_schema"),
                parameters={"postgres_schema": postgres_schema},
            )
        yield connection
