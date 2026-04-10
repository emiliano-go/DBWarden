from dbwarden.database import queries
from dbwarden.database.queries import QueryMethod


def test_postgres_migration_table_query_uses_bigserial(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "BIGSERIAL PRIMARY KEY" in sql
    assert "AUTOINCREMENT" not in sql


def test_sqlite_migration_table_query_uses_autoincrement(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "sqlite")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "AUTOINCREMENT" in sql
