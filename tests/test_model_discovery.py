import pytest
import tempfile
import os
from pathlib import Path

import dbwarden.engine.model_discovery as model_discovery
from dbwarden.engine.model_discovery import (
    load_model_from_path,
    discover_models_in_directory,
    extract_column_info,
    extract_table_from_model,
    generate_create_table_sql,
    generate_drop_object_sql,
    generate_drop_table_sql,
    ModelColumn,
    ModelTable,
)


class TestModelDiscovery:
    """Tests for SQLAlchemy model discovery."""

    def test_load_model_from_python_file(self):
        """Test loading a model from a Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_content = """
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
"""
            model_path = os.path.join(tmpdir, "models.py")
            with open(model_path, "w") as f:
                f.write(model_content)

            module = load_model_from_path(model_path)

            assert module is not None
            assert hasattr(module, "User")
            assert module.User.__tablename__ == "users"

    def test_load_model_nonexistent_file(self):
        """Test loading from nonexistent file returns None."""
        result = load_model_from_path("/nonexistent/path/models.py")
        assert result is None

    def test_discover_models_in_directory(self):
        """Test discovering model files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "models")
            os.makedirs(subdir)

            with open(os.path.join(subdir, "user.py"), "w") as f:
                f.write("# User model")

            with open(os.path.join(subdir, "post.py"), "w") as f:
                f.write("# Post model")

            with open(os.path.join(subdir, "__init__.py"), "w") as f:
                f.write("")

            files = discover_models_in_directory(subdir)

            assert len(files) == 2
            assert any("user.py" in f for f in files)
            assert any("post.py" in f for f in files)

    def test_discover_models_includes_regular_files(self):
        """Test that regular Python files are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "models")
            os.makedirs(subdir)

            with open(os.path.join(subdir, "__init__.py"), "w") as f:
                f.write("")

            with open(os.path.join(subdir, "user.py"), "w") as f:
                f.write("# User model")

            files = discover_models_in_directory(subdir)

            assert len(files) == 1
            assert "user.py" in files[0]

    def test_discover_models_empty_directory(self):
        """Test discovering in empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = discover_models_in_directory(tmpdir)
            assert files == []


class TestModelColumn:
    """Tests for ModelColumn class."""

    def test_model_column_creation(self):
        """Test creating a ModelColumn."""
        col = ModelColumn(
            name="id",
            type="INTEGER",
            nullable=False,
            primary_key=True,
            unique=True,
            default=None,
            foreign_key=None,
        )

        assert col.name == "id"
        assert col.type == "INTEGER"
        assert col.nullable == False
        assert col.primary_key == True

    def test_model_column_to_dict(self):
        """Test ModelColumn to_dict method."""
        col = ModelColumn(
            name="email",
            type="VARCHAR(255)",
            nullable=False,
            primary_key=False,
            unique=True,
            default=None,
            foreign_key=None,
        )

        col_dict = col.to_dict()

        assert col_dict["name"] == "email"
        assert col_dict["type"] == "VARCHAR(255)"
        assert col_dict["unique"] == True

    def test_model_column_to_dict_includes_codec(self):
        col = ModelColumn(
            name="data",
            type="String",
            nullable=False,
            primary_key=False,
            unique=False,
            default=None,
            foreign_key=None,
            codec="ZSTD(3)",
        )

        col_dict = col.to_dict()
        assert col_dict["codec"] == "ZSTD(3)"


class TestModelTable:
    """Tests for ModelTable class."""

    def test_model_table_creation(self):
        """Test creating a ModelTable."""
        columns = [
            ModelColumn("id", "INTEGER", False, True, False, None, None),
            ModelColumn("name", "VARCHAR(100)", True, False, False, None, None),
        ]

        table = ModelTable(name="users", columns=columns)

        assert table.name == "users"
        assert len(table.columns) == 2

    def test_model_table_to_dict(self):
        """Test ModelTable to_dict method."""
        columns = [
            ModelColumn("id", "INTEGER", False, True, False, None, None),
        ]

        table = ModelTable(name="users", columns=columns)
        table_dict = table.to_dict()

        assert table_dict["name"] == "users"
        assert len(table_dict["columns"]) == 1

    def test_model_table_to_dict_includes_clickhouse_options(self):
        columns = [
            ModelColumn("id", "UInt64", False, True, False, None, None),
        ]

        table = ModelTable(
            name="events",
            columns=columns,
            clickhouse_options={"clickhouse_engine": "MergeTree"},
        )

        table_dict = table.to_dict()
        assert table_dict["clickhouse_options"]["clickhouse_engine"] == "MergeTree"


class TestSQLGeneration:
    """Tests for SQL generation from models."""

    def test_generate_create_table_sql(self):
        """Test generating CREATE TABLE SQL."""
        columns = [
            ModelColumn("id", "INTEGER", False, True, False, None, None),
            ModelColumn("name", "VARCHAR(100)", False, False, False, None, None),
            ModelColumn("email", "VARCHAR(255)", False, False, True, None, None),
        ]

        table = ModelTable(name="users", columns=columns)
        sql = generate_create_table_sql(table)

        assert "CREATE TABLE IF NOT EXISTS users" in sql
        assert "NOT NULL" in sql
        assert "PRIMARY KEY" in sql
        assert "UNIQUE" in sql

    def test_generate_drop_table_sql(self):
        """Test generating DROP TABLE SQL."""
        sql = generate_drop_table_sql("users")
        assert sql == "DROP TABLE users"

    def test_generate_create_table_with_foreign_key(self):
        """Test generating CREATE TABLE with foreign key."""
        columns = [
            ModelColumn("id", "INTEGER", False, True, False, None, None),
            ModelColumn("user_id", "INTEGER", False, False, False, None, "users(id)"),
        ]

        table = ModelTable(name="posts", columns=columns)
        sql = generate_create_table_sql(table)

        assert "user_id INTEGER NOT NULL REFERENCES users(id)" in sql

    def test_generate_clickhouse_create_table_sql_with_options(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("region", "String", False, True, False, None, None),
            ModelColumn("event_time", "DateTime", False, False, False, None, None),
        ]

        table = ModelTable(
            name="events",
            columns=columns,
            clickhouse_options={
                "clickhouse_engine": ("ReplacingMergeTree", "version_column"),
                "clickhouse_order_by": ["region", "event_time"],
                "clickhouse_primary_key": "region",
                "clickhouse_partition_by": "toYYYYMM(event_time)",
                "clickhouse_sample_by": "intHash64(region)",
                "clickhouse_ttl": ["event_time + INTERVAL 1 MONTH DELETE"],
            },
        )

        sql = generate_create_table_sql(table)

        assert "ENGINE = ReplacingMergeTree(version_column)" in sql
        assert "ORDER BY (region, event_time)" in sql
        assert "PRIMARY KEY region" in sql
        assert "PARTITION BY toYYYYMM(event_time)" in sql
        assert "SAMPLE BY intHash64(region)" in sql
        assert "TTL event_time + INTERVAL 1 MONTH DELETE" in sql

    def test_generate_clickhouse_create_table_sql_with_composite_primary_key(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("region", "String", False, False, False, None, None),
            ModelColumn("event_time", "DateTime", False, False, False, None, None),
        ]

        table = ModelTable(
            name="events",
            columns=columns,
            clickhouse_options={
                "clickhouse_order_by": ["region", "event_time"],
                "clickhouse_primary_key": ["region", "event_time"],
            },
        )

        sql = generate_create_table_sql(table)

        assert "PRIMARY KEY (region, event_time)" in sql

    def test_generate_clickhouse_create_table_sql_with_codec(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("data", "String", False, False, False, None, None, codec="ZSTD(3)"),
        ]

        table = ModelTable(name="events", columns=columns)
        sql = generate_create_table_sql(table)

        assert "data String NOT NULL CODEC(ZSTD(3))" in sql
        assert "ENGINE = MergeTree()" in sql

    def test_generate_clickhouse_create_table_sql_with_projection(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("author", "String", False, False, False, None, None),
            ModelColumn("created_at", "DateTime", False, False, False, None, None),
        ]

        table = ModelTable(
            name="posts",
            columns=columns,
            clickhouse_options={
                "clickhouse_order_by": ["author", "created_at"],
                "clickhouse_projections": [
                    {"name": "by_author", "query": "SELECT * ORDER BY author"}
                ],
            },
        )

        sql = generate_create_table_sql(table)

        assert "PROJECTION by_author (SELECT * ORDER BY author)" in sql

    def test_generate_clickhouse_materialized_view_sql(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("group_col", "String", False, True, False, None, None),
            ModelColumn("total", "UInt64", False, False, False, None, None),
        ]

        table = ModelTable(
            name="mv_name",
            columns=columns,
            clickhouse_options={
                "clickhouse_mv": True,
                "clickhouse_mv_query": "SELECT group_col, count() AS total FROM source_table GROUP BY group_col",
                "clickhouse_mv_engine": "SummingMergeTree",
                "clickhouse_mv_order_by": ["group_col"],
            },
            object_type="materialized_view",
        )

        sql = generate_create_table_sql(table)

        assert "CREATE MATERIALIZED VIEW IF NOT EXISTS mv_name" in sql
        assert "ENGINE = SummingMergeTree()" in sql
        assert "ORDER BY (group_col)" in sql
        assert "AS SELECT group_col, count() AS total FROM source_table GROUP BY group_col" in sql

    def test_generate_drop_object_sql_for_materialized_view(self):
        table = ModelTable(
            name="mv_name",
            columns=[],
            object_type="materialized_view",
        )

        assert generate_drop_object_sql(table) == "DROP VIEW mv_name"

    def test_generate_replicated_clickhouse_engine_with_zookeeper(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("id", "UInt64", False, True, False, None, None),
            ModelColumn("data", "String", False, False, False, None, None),
        ]

        table = ModelTable(
            name="replicated_table",
            columns=columns,
            clickhouse_options={
                "clickhouse_engine": "ReplicatedMergeTree",
                "clickhouse_zookeeper_path": "'/clickhouse/tables/shard1'",
                "clickhouse_replica_name": "'{replica}'",
                "clickhouse_order_by": ["id"],
            },
        )

        sql = generate_create_table_sql(table)

        assert "ENGINE = ReplicatedMergeTree('/clickhouse/tables/shard1', '{replica}')" in sql

    def test_generate_replicated_clickhouse_engine_with_zookeeper_tuple(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        table = ModelTable(
            name="replicated_table",
            columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
            clickhouse_options={
                "clickhouse_engine": ("ReplicatedReplacingMergeTree", "ver_col"),
                "clickhouse_zookeeper_path": "'/zk/path'",
                "clickhouse_replica_name": "'{replica}'",
                "clickhouse_order_by": ["id"],
            },
        )

        sql = generate_create_table_sql(table)

        assert "ENGINE = ReplicatedReplacingMergeTree('/zk/path', '{replica}', ver_col)" in sql

    def test_generate_dictionary_sql(self, monkeypatch):
        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        columns = [
            ModelColumn("code", "String", False, True, False, None, None),
            ModelColumn("name", "String", False, False, False, None, None),
        ]

        table = ModelTable(
            name="country_codes",
            columns=columns,
            clickhouse_options={
                "clickhouse_dictionary": True,
                "clickhouse_dict_layout": "FLAT()",
                "clickhouse_dict_source": "CLICKHOUSE(HOST 'localhost' TABLE 'source')",
                "clickhouse_dict_lifetime": "MIN 0 MAX 3600",
                "clickhouse_dict_primary_key": "code",
            },
            object_type="dictionary",
        )

        sql = generate_create_table_sql(table)

        assert "CREATE DICTIONARY IF NOT EXISTS country_codes" in sql
        assert "PRIMARY KEY code" in sql
        assert "SOURCE(CLICKHOUSE(HOST 'localhost' TABLE 'source'))" in sql
        assert "LIFETIME(MIN 0 MAX 3600)" in sql
        assert "LAYOUT(FLAT())" in sql

    def test_generate_drop_dictionary_sql(self):
        table = ModelTable(
            name="country_codes",
            columns=[],
            object_type="dictionary",
        )

        assert generate_drop_object_sql(table) == "DROP DICTIONARY country_codes"


class TestColumnExtraction:
    """Tests for column information extraction."""

    def test_extract_column_from_sqlalchemy_column(self):
        """Test extracting column info from SQLAlchemy column."""
        from sqlalchemy import Column, Integer, String

        col_obj = Column("id", Integer, primary_key=True)

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.name == "id"
        assert col.primary_key == True

    def test_extract_column_nullable(self):
        """Test extracting nullable column."""
        from sqlalchemy import Column, String

        col_obj = Column("name", String(100), nullable=True)

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.nullable == True

    def test_extract_column_not_nullable(self):
        """Test extracting non-nullable column."""
        from sqlalchemy import Column, String

        col_obj = Column("name", String(100), nullable=False)

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.nullable == False

    def test_extract_column_translates_jsonb_to_text_for_sqlite(self):
        from sqlalchemy import Column
        from sqlalchemy.dialects.postgresql import JSONB

        col_obj = Column("payload", JSONB)

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.type == "TEXT"

    def test_extract_column_falls_back_unknown_type_to_text_for_sqlite(self):
        from sqlalchemy import Column
        from sqlalchemy.types import UserDefinedType

        class Geography(UserDefinedType):
            def get_col_spec(self, **kw):
                return "GEOGRAPHY"

        col_obj = Column("location", Geography())

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.type == "TEXT"

    def test_extract_column_uses_clickhouse_type_and_codec_hints(self, monkeypatch):
        from sqlalchemy import Column, String

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        col_obj = Column(
            "payload",
            String,
            info={
                "clickhouse_type": "LowCardinality(String)",
                "clickhouse_codec": "ZSTD(3)",
            },
        )

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.type == "LowCardinality(String)"
        assert col.codec == "ZSTD(3)"

    def test_extract_column_preserves_clickhouse_user_defined_type(self, monkeypatch):
        from sqlalchemy import Column
        from sqlalchemy.types import UserDefinedType

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        class LowCardinalityString(UserDefinedType):
            def get_col_spec(self, **kw):
                return "LowCardinality(String)"

        col_obj = Column("payload", LowCardinalityString())

        col = extract_column_info(col_obj)

        assert col is not None
        assert col.type == "LowCardinality(String)"

    def test_extract_table_from_model_uses_clickhouse_table_args(self, monkeypatch):
        from sqlalchemy import Column, MetaData, String, Table

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        class Event:
            __tablename__ = "events"
            __table_args__ = {
                "clickhouse_engine": "SummingMergeTree",
                "clickhouse_order_by": ["region"],
            }
            __table__ = Table(
                "events",
                MetaData(),
                Column("region", String, primary_key=True),
            )

        table = extract_table_from_model(Event, db_name="primary")

        assert table is not None
        assert table.clickhouse_options["clickhouse_engine"] == "SummingMergeTree"
        assert table.clickhouse_options["clickhouse_order_by"] == ["region"]

    def test_extract_table_from_model_sets_materialized_view_object_type(self, monkeypatch):
        from sqlalchemy import Column, MetaData, String, Table

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        class EventView:
            __tablename__ = "mv_name"
            __table_args__ = {
                "clickhouse_mv": True,
                "clickhouse_mv_query": "SELECT region FROM source_table",
            }
            __table__ = Table(
                "mv_name",
                MetaData(),
                Column("region", String, primary_key=True),
            )

        table = extract_table_from_model(EventView, db_name="primary")

        assert table is not None
        assert table.object_type == "materialized_view"

    def test_extract_table_from_model_rejects_invalid_clickhouse_primary_key_prefix(self, monkeypatch):
        from sqlalchemy import Column, MetaData, String, Table

        monkeypatch.setattr(model_discovery, "_get_backend_name", lambda db_name=None: "clickhouse")

        class Event:
            __tablename__ = "events"
            __table_args__ = {
                "clickhouse_order_by": ["region", "event_time"],
                "clickhouse_primary_key": ["event_time"],
            }
            __table__ = Table(
                "events",
                MetaData(),
                Column("region", String),
                Column("event_time", String),
            )

        table = extract_table_from_model(Event, db_name="primary")

        assert table is None
