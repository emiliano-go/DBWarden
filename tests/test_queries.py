from dbwarden.database import queries
from dbwarden.database.queries import QueryMethod


def test_postgres_migration_table_query_uses_bigserial(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda: "postgresql")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "BIGSERIAL PRIMARY KEY" in sql
    assert "AUTOINCREMENT" not in sql


def test_sqlite_migration_table_query_uses_autoincrement(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda: "sqlite")
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "AUTOINCREMENT" in sql
