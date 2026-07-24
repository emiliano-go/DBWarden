from __future__ import annotations


class SQLiteSandboxProvider:
    """In-memory SQLite sandbox - no Docker required."""

    def start(self) -> str:
        return "sqlite:///:memory:"

    def stop(self) -> None:
        pass

    def get_database_type(self) -> str:
        return "sqlite"
