import os
import tempfile
from pathlib import Path

from dbwarden.commands.generate_models import _parse_type, _format_default, _generate_table_code


def test_parse_integer():
    assert _parse_type("INTEGER") == "Integer"
    assert _parse_type("BIGINT") == "BigInteger"
    assert _parse_type("SMALLINT") == "SmallInteger"


def test_parse_string():
    assert _parse_type("VARCHAR(100)") == "String(length=100)"
    assert _parse_type("CHAR(10)") == "String(length=10)"
    assert _parse_type("TEXT") == "Text"


def test_parse_boolean():
    assert _parse_type("BOOLEAN") == "Boolean"
    assert _parse_type("TINYINT(1)") == "Boolean"


def test_parse_temporal():
    assert _parse_type("DATE") == "Date"
    assert _parse_type("DATETIME") == "DateTime"
    assert _parse_type("TIMESTAMP") == "DateTime"


def test_parse_numeric():
    result = _parse_type("DECIMAL(10,2)")
    assert "Numeric" in result
    assert "precision=10" in result
    assert "scale=2" in result


def test_parse_clickhouse_nullable():
    assert _parse_type("Nullable(String)") == "String"


def test_parse_postgresql_specific_types():
    assert _parse_type("JSONB", dialect="postgresql") == "JSONB"
    assert _parse_type("UUID", dialect="postgresql") == "UUID(as_uuid=True)"
    assert _parse_type("INTEGER[]", dialect="postgresql") == "ARRAY(Integer)"


def test_parse_clickhouse_types():
    assert _parse_type("Int32", dialect="clickhouse") == "Integer"
    assert _parse_type("UInt64", dialect="clickhouse") == "BigInteger"
    assert _parse_type("Float64", dialect="clickhouse") == "Float"


def test_format_default():
    assert _format_default(None) is None
    assert _format_default("CURRENT_TIMESTAMP") == "func.now()"
    assert _format_default("42") == "42"
    assert _format_default("hello") == "'hello'"


def test_generate_table_code_simple():
    columns = [
        {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None},
        {"name": "name", "type": "VARCHAR(100)", "nullable": True, "default": None, "primary_key": False, "unique": False, "foreign_key": None},
    ]
    code = _generate_table_code("users", columns)
    assert "class Users(Base):" in code
    assert "__tablename__ = 'users'" in code
    assert "primary_key=True" in code
    assert "String(length=100)" in code


def test_generate_table_code_with_foreign_key():
    columns = [
        {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None},
        {"name": "user_id", "type": "INTEGER", "nullable": True, "default": None, "primary_key": False, "unique": False, "foreign_key": "users(id)"},
    ]
    code = _generate_table_code("posts", columns)
    assert "ForeignKey('users(id)')" in code


def test_generate_table_code_with_postgresql_meta():
    columns = [
        {
            "name": "email",
            "type": "VARCHAR(255)",
            "nullable": False,
            "default": None,
            "primary_key": False,
            "unique": True,
            "foreign_key": None,
            "comment": "Primary contact email",
            "pg_meta": {"pg_collation": "en_US.UTF-8"},
            "dialect": "postgresql",
        }
    ]
    code = _generate_table_code(
        "users",
        columns,
        object_type="table",
        pg_meta={"comment": "Core user accounts", "pg_indexes": [{"name": "ix_users_email", "columns": ["email"], "unique": True}]},
    )
    assert "class Meta(PGTableMeta):" in code
    assert "comment = 'Core user accounts'" in code
    assert "class email(PGColumnMeta):" in code
    assert "pg_collation = 'en_US.UTF-8'" in code


def test_write_models_postgresql_emits_dialect_imports_and_meta():
    with tempfile.TemporaryDirectory() as tmpdir:
        from dbwarden.commands.generate_models import _write_models

        tables = [
            {
                "name": "users",
                "columns": [
                    {
                        "name": "id",
                        "type": "UUID",
                        "nullable": False,
                        "default": None,
                        "primary_key": True,
                        "unique": False,
                        "foreign_key": None,
                        "autoincrement": False,
                        "dialect": "postgresql",
                    },
                    {
                        "name": "payload",
                        "type": "JSONB",
                        "nullable": True,
                        "default": None,
                        "primary_key": False,
                        "unique": False,
                        "foreign_key": None,
                        "autoincrement": False,
                        "dialect": "postgresql",
                        "comment": "Payload",
                        "pg_meta": {"pg_collation": "en_US.UTF-8"},
                    },
                ],
                "clickhouse_options": None,
                "object_type": "table",
                "dialect": "postgresql",
                "pg_meta": {"comment": "Users table"},
            }
        ]
        _write_models(tmpdir, tables, single_file=True)
        content = Path(tmpdir, "models.py").read_text()
        assert "from sqlalchemy.dialects.postgresql import JSONB, UUID" in content
        assert "class Meta(PGTableMeta):" in content
        assert "comment = 'Users table'" in content


def test_write_models_single_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from dbwarden.config import set_dev_mode
            from dbwarden.commands.generate_models import _write_models

            set_dev_mode(False)
            tables = [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None, "autoincrement": True},
                        {"name": "email", "type": "VARCHAR(255)", "nullable": True, "default": None, "primary_key": False, "unique": True, "foreign_key": None},
                    ],
                    "clickhouse_options": None,
                    "object_type": "table",
                }
            ]
            _write_models(tmpdir, tables, single_file=True)
            model_path = Path(tmpdir, "models.py")
            assert model_path.exists()
            content = model_path.read_text()
            assert "class Users(Base):" in content
            assert "__tablename__ = 'users'" in content
        finally:
            os.chdir(old_cwd)


def test_write_models_per_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from dbwarden.config import set_dev_mode
            from dbwarden.commands.generate_models import _write_models

            set_dev_mode(False)
            tables = [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None, "autoincrement": True},
                    ],
                    "clickhouse_options": None,
                    "object_type": "table",
                },
                {
                    "name": "posts",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None, "autoincrement": True},
                    ],
                    "clickhouse_options": None,
                    "object_type": "table",
                },
            ]
            _write_models(tmpdir, tables, single_file=False)
            assert Path(tmpdir, "users.py").exists()
            assert Path(tmpdir, "posts.py").exists()
            users_content = Path(tmpdir, "users.py").read_text()
            assert "Base = declarative_base()" in users_content
        finally:
            os.chdir(old_cwd)


def test_generate_models_with_db_connection():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from dbwarden.config import set_dev_mode
            from dbwarden.database.connection import get_db_connection
            from dbwarden.commands.generate_models import generate_models_cmd
            from sqlalchemy import text

            set_dev_mode(False)
            db_path = f"sqlite:///./{Path(tmpdir).name}.db"
            Path(tmpdir, "dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                f"database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='{db_path}')\n",
                encoding="utf-8",
            )

            with get_db_connection(None) as conn:
                conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE)"))
                conn.execute(text("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, FOREIGN KEY (user_id) REFERENCES users(id))"))

            generate_models_cmd(
                output=tmpdir,
                tables=None,
                exclude_tables=None,
                clickhouse_engines=False,
                relationships=False,
                dialect=None,
                single_file=True,
                database=None,
            )

            model_file = Path(tmpdir, "models.py")
            assert model_file.exists()
            content = model_file.read_text()
            assert "class Users(Base):" in content or "class User(Base):" in content
            assert "class Posts(Base):" in content
            assert "ForeignKey" in content
        finally:
            os.chdir(old_cwd)


def test_generate_models_with_tables_filter():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            from dbwarden.config import set_dev_mode
            from dbwarden.database.connection import get_db_connection
            from dbwarden.commands.generate_models import generate_models_cmd
            from sqlalchemy import text

            set_dev_mode(False)
            db_path = f"sqlite:///./{Path(tmpdir).name}.db"
            Path(tmpdir, "dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                f"database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='{db_path}')\n",
                encoding="utf-8",
            )

            with get_db_connection(None) as conn:
                conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
                conn.execute(text("CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT)"))

            generate_models_cmd(
                output=tmpdir,
                tables="users",
                exclude_tables=None,
                clickhouse_engines=False,
                relationships=False,
                dialect=None,
                single_file=True,
                database=None,
            )

            content = Path(tmpdir, "models.py").read_text()
            assert "class Users(Base):" in content or "class User(Base):" in content
            assert "posts" not in content.lower() or "Posts" not in content
        finally:
            os.chdir(old_cwd)


class TestClickHouseGenerateModels:
    def test_render_ch_meta_simple(self):
        from dbwarden.commands.generate_models import _render_ch_meta
        meta_lines = _render_ch_meta(
            columns=[],
            options={"ch_engine": "MergeTree", "ch_order_by": ["id"]},
            object_type="table",
        )
        assert any("ch_engine = 'MergeTree'" in line for line in meta_lines)
        assert any("ch_order_by = ['id']" in line for line in meta_lines)

    def test_render_ch_meta_with_ch_settings(self):
        from dbwarden.commands.generate_models import _render_ch_meta
        meta_lines = _render_ch_meta(
            columns=[],
            options={"ch_engine": "MergeTree", "ch_order_by": ["id"], "ch_settings": {"allow_nullable_key": 1}},
            object_type="table",
        )
        assert any("ch_settings = {'allow_nullable_key': 1}" in line for line in meta_lines)

    def test_render_ch_meta_with_engine_spec(self):
        from dbwarden.commands.generate_models import _render_ch_meta
        from dbwarden.schema.engine import ChEngineSpec
        engine = ChEngineSpec(name="ReplicatedMergeTree", args=("/zk/path", "{replica}"))
        meta_lines = _render_ch_meta(
            columns=[],
            options={"ch_engine_raw": engine, "ch_order_by": ["id"]},
            object_type="table",
        )
        assert any("ch_engine = ChEngineSpec(" in line for line in meta_lines)
        assert any("ReplicatedMergeTree" in line for line in meta_lines)

    def test_generate_table_code_clickhouse_engine(self):
        columns = [
            {"name": "id", "type": "UInt64", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None},
            {"name": "name", "type": "String", "nullable": True, "default": None, "primary_key": False, "unique": False, "foreign_key": None},
        ]
        code = _generate_table_code(
            "events",
            columns,
            object_type="table",
            clickhouse_options={
                "ch_engine": "MergeTree",
                "ch_order_by": ["id"],
            },
        )
        assert "class Events(Base):" in code
        assert "__tablename__ = 'events'" in code
        assert "class Meta(CHTableMeta):" in code
        assert "ch_engine = 'MergeTree'" in code

    def test_generate_table_code_clickhouse_column_ch_meta(self):
        columns = [
            {"name": "id", "type": "UInt64", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None},
            {
                "name": "payload",
                "type": "String",
                "nullable": True,
                "default": None,
                "primary_key": False,
                "unique": False,
                "foreign_key": None,
                "ch_meta": {"ch_codec": "ZSTD(3)", "ch_type": "String"},
            },
        ]
        code = _generate_table_code(
            "events",
            columns,
            object_type="table",
            clickhouse_options={
                "ch_engine": "MergeTree",
                "ch_order_by": ["id"],
            },
        )
        assert "ch_codec = 'ZSTD(3)'" in code

    def test_parse_clickhouse_nullable_type(self):
        assert _parse_type("Nullable(String)") == "String"
        assert _parse_type("Nullable(Int32)") == "Integer"

    def test_generate_table_code_clickhouse_high_precision_datetime(self):
        columns = [
            {"name": "id", "type": "UInt64", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None},
            {"name": "ts", "type": "DateTime64(3)", "nullable": False, "default": None, "primary_key": False, "unique": False, "foreign_key": None},
        ]
        code = _generate_table_code(
            "events",
            columns,
            object_type="table",
        )
        assert "DateTime" in code

    def test_parse_clickhouse_types_extra(self):
        assert _parse_type("Int8", dialect="clickhouse") == "SmallInteger"
        assert _parse_type("Int16", dialect="clickhouse") == "SmallInteger"
        assert _parse_type("Int64", dialect="clickhouse") == "BigInteger"
        assert _parse_type("Float32", dialect="clickhouse") == "Float"
        assert _parse_type("String", dialect="clickhouse") == "String"
        assert _parse_type("Date", dialect="clickhouse") == "Date"
        assert _parse_type("DateTime", dialect="clickhouse") == "DateTime"

    def test_write_models_clickhouse_emits_meta_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from dbwarden.commands.generate_models import _write_models

            tables = [
                {
                    "name": "events",
                    "columns": [
                        {"name": "id", "type": "UInt64", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None, "autoincrement": False},
                    ],
                    "clickhouse_options": {"ch_engine": "MergeTree", "ch_order_by": ["id"]},
                    "object_type": "table",
                }
            ]
            _write_models(tmpdir, tables, single_file=True)
            content = Path(tmpdir, "models.py").read_text()
            assert "CHColumnMeta" in content
            assert "CHTableMeta" in content
            assert "from dbwarden import CHColumnMeta, CHTableMeta" in content

    def test_write_models_clickhouse_ch_engine_spec_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from dbwarden.commands.generate_models import _write_models
            from dbwarden.schema.engine import ChEngineSpec

            tables = [
                {
                    "name": "events",
                    "columns": [
                        {"name": "id", "type": "UInt64", "nullable": False, "default": None, "primary_key": True, "unique": False, "foreign_key": None, "autoincrement": False},
                    ],
                    "clickhouse_options": {"ch_engine_raw": ChEngineSpec("MergeTree"), "ch_order_by": ["id"]},
                    "object_type": "table",
                }
            ]
            _write_models(tmpdir, tables, single_file=True)
            content = Path(tmpdir, "models.py").read_text()
            assert "ChEngineSpec" in content
            assert "from dbwarden import CHColumnMeta, CHTableMeta, ChEngineSpec" in content

    def test_generate_table_code_ch_materialized_view(self):
        columns = [
            {"name": "group_col", "type": "String", "nullable": False, "default": None, "primary_key": False, "unique": False, "foreign_key": None},
            {"name": "total", "type": "UInt64", "nullable": False, "default": None, "primary_key": False, "unique": False, "foreign_key": None},
        ]
        code = _generate_table_code(
            "mv_name",
            columns,
            object_type="materialized_view",
            clickhouse_options={
                "ch_object_type": "materialized_view",
                "ch_select_statement": "SELECT group_col, count() AS total FROM source GROUP BY group_col",
                "ch_engine": "SummingMergeTree",
                "ch_order_by": ["group_col"],
            },
        )
        assert "class MvName(Base):" in code
        assert "ch_select_statement" in code
        assert "__tablename__ = 'mv_name'" in code
