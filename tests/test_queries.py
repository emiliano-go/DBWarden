from dbwarden.database import queries
from dbwarden.database.queries import QueryMethod, DEFAULT_POSTGRES_SCHEMA


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


def test_postgres_schema_default_public(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    class FakeConfig:
        postgres_schema = None
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "public._dbwarden_migrations" in sql


def test_postgres_schema_custom_schema(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    class FakeConfig:
        postgres_schema = "myapp"
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    sql = queries.get_query(QueryMethod.CREATE_MIGRATIONS_TABLE)
    assert "myapp._dbwarden_migrations" in sql
    assert "public." not in sql


def test_postgres_seed_query_uses_schema(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    class FakeConfig:
        postgres_schema = "custom"
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    sql = queries.get_seed_query(QueryMethod.CREATE_SEEDS_TABLE)
    assert "custom._dbwarden_seeds" in sql
    assert "public." not in sql


def test_postgres_check_table_exists_uses_schema(monkeypatch):
    monkeypatch.setattr(queries, "_get_backend_name", lambda db_name=None: "postgresql")
    class FakeConfig:
        postgres_schema = "myschema"
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    sql = queries.get_query(QueryMethod.CHECK_IF_MIGRATIONS_TABLE_EXISTS)
    assert "myschema" in sql


def test_get_schema_name_default(monkeypatch):
    def _raise(*_a, **_kw):
        raise Exception("no config")
    monkeypatch.setattr(queries, "get_database", _raise)
    assert queries.get_schema_name() == DEFAULT_POSTGRES_SCHEMA


def test_get_schema_name_from_config(monkeypatch):
    class FakeConfig:
        postgres_schema = "tenant"
    monkeypatch.setattr(queries, "get_database", lambda db_name=None: FakeConfig())
    assert queries.get_schema_name() == "tenant"
