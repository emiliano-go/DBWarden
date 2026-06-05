"""Sandbox database providers for dry-run and sandbox migration testing."""

import os
from abc import ABC, abstractmethod
from typing import Optional


class SandboxProvider(ABC):
    """Abstract base class for sandbox database providers."""

    @abstractmethod
    def start(self) -> str:
        """Start the sandbox database and return its connection URL."""

    @abstractmethod
    def stop(self) -> None:
        """Stop and clean up the sandbox database."""

    @abstractmethod
    def get_database_type(self) -> str:
        """Return the database type string (e.g. 'sqlite', 'clickhouse')."""


class SQLiteSandboxProvider(SandboxProvider):
    """In-memory SQLite sandbox - no Docker required."""

    def start(self) -> str:
        return "sqlite:///:memory:"

    def stop(self) -> None:
        pass

    def get_database_type(self) -> str:
        return "sqlite"


_HAS_TESTCONTAINERS: bool = False
try:
    import testcontainers  # noqa: F401
    _HAS_TESTCONTAINERS = True
except ImportError:
    pass


def create_sandbox_provider(database_type: str) -> SandboxProvider:
    """Create the right sandbox provider for the given database type.

    For ClickHouse, PostgreSQL, and MySQL this requires Docker and the
    ``testcontainers`` package.  Falls back to :class:`SQLiteSandboxProvider`
    when testcontainers is not installed.
    """
    if database_type == "sqlite":
        return SQLiteSandboxProvider()

    if not _HAS_TESTCONTAINERS:
        return SQLiteSandboxProvider()

    return _create_testcontainers_provider(database_type)


def _create_testcontainers_provider(database_type: str) -> SandboxProvider:
    if database_type == "clickhouse":
        return ClickHouseTestcontainersProvider()
    if database_type == "postgresql":
        return PostgresTestcontainersProvider()
    if database_type == "mysql":
        return MySQLTestcontainersProvider()
    return SQLiteSandboxProvider()


class _TestcontainersProvider(SandboxProvider):
    """Base for providers backed by testcontainers."""

    CONTAINER_CLS = None
    DB_DRIVER: str = ""
    DB_TYPE: str = ""

    def __init__(self) -> None:
        self._container = None

    def start(self) -> str:
        if self.CONTAINER_CLS is None:
            return SQLiteSandboxProvider().start()

        tc = __import__("testcontainers", fromlist=[self.CONTAINER_CLS])
        cls = getattr(tc, self.CONTAINER_CLS)
        self._container = cls()
        self._container.start()
        return self._build_url()

    def stop(self) -> None:
        if self._container is not None:
            self._container.stop()
            self._container = None

    def get_database_type(self) -> str:
        return self.DB_TYPE

    def _build_url(self) -> str:
        raise NotImplementedError


class ClickHouseTestcontainersProvider(_TestcontainersProvider):
    CONTAINER_CLS = "ClickHouseContainer"
    DB_DRIVER = "clickhousedb"
    DB_TYPE = "clickhouse"

    def _build_url(self) -> str:
        port = self._container.get_exposed_port(8123)
        host = self._container.get_container_host_ip()
        return f"clickhousedb://default:@:{port}/default"


class PostgresTestcontainersProvider(_TestcontainersProvider):
    CONTAINER_CLS = "PostgresContainer"
    DB_DRIVER = "postgresql"
    DB_TYPE = "postgresql"

    def _build_url(self) -> str:
        return self._container.get_connection_url()


class MySQLTestcontainersProvider(_TestcontainersProvider):
    CONTAINER_CLS = "MySQLContainer"
    DB_DRIVER = "mysql"
    DB_TYPE = "mysql"

    def _build_url(self) -> str:
        return self._container.get_connection_url()
