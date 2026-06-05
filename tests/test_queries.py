from dbwarden.database import queries
from dbwarden.database.queries import QueryMethod


def test_postgres_migration_table_query_uses_filename(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "filename" in sql
    assert "BIGSERIAL" not in sql


def test_sqlite_migration_table_query_uses_filename(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "sqlite")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "filename" in sql
    assert "AUTOINCREMENT" not in sql


def test_query_uses_custom_migration_table(monkeypatch):
    class FakeConfig:
        migration_table = "custom_migrations"

    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "sqlite")
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    sql = queries.get_query(QueryMethod.GET_MIGRATED_VERSIONS)
    assert "custom_migrations" in sql
    assert "dbwarden_migrations" not in sql
