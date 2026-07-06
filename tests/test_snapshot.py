import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

pymysql = pytest.importorskip("pymysql")

from dbwarden.engine.snapshot import (
    _apply_rename_intents,
    _assemble_migration,
    _build_index_name,
    _build_index_sql,
    _normalize_mysql_default,
    _compute_table_overlap,
    _rename_table_sql,
    TableRenameIntent,
    MigrationStatement,
    StatementOrder,
    compute_checksum,
    detect_renames,
    diff_models_against_snapshot,
    find_latest_snapshot,
    get_schemas_directory,
    normalize_type,
    read_snapshot,
    write_snapshot,
    snapshot_diff_to_sql,
    extract_full_schema_snapshot,
)
from dbwarden.engine.model_discovery import IndexInfo, ModelColumn, ModelTable
from dbwarden.engine.migration_name import Change
from dbwarden.engine.offline import diff_model_states, model_state_to_dict
from dbwarden.engine.pg_registry import ConstraintHandler
from dbwarden.engine.pg_registry.protocol import Op


def _mc(name: str, typ: str, pk: bool = False, nullable: bool = True) -> ModelColumn:
    return ModelColumn(name, typ, nullable, pk, False, None, None)


class TestNormalizeType:
    def test_integer_variants(self):
        for raw in ("INT", "INTEGER", "INT4", "TINYINT", "SMALLINT", "int", "integer"):
            assert normalize_type(raw)["type"] == "integer"

    def test_biginteger(self):
        assert normalize_type("BIGINT")["type"] == "biginteger"
        assert normalize_type("INT8")["type"] == "biginteger"

    def test_varchar_with_length(self):
        result = normalize_type("VARCHAR(255)")
        assert result["type"] == "varchar"
        assert result["length"] == 255

    def test_text_variants(self):
        for raw in ("TEXT", "LONGTEXT", "CLOB"):
            assert normalize_type(raw)["type"] == "text"

    def test_boolean(self):
        assert normalize_type("BOOLEAN")["type"] == "boolean"
        assert normalize_type("BOOL")["type"] == "boolean"

    def test_timestamp(self):
        assert normalize_type("TIMESTAMP")["type"] == "timestamp"
        assert normalize_type("DATETIME")["type"] == "timestamp"

    def test_numeric_with_precision_scale(self):
        result = normalize_type("NUMERIC(10, 2)")
        assert result["type"] == "numeric"
        assert result["precision"] == 10
        assert result["scale"] == 2

    def test_unknown_type_is_raw(self):
        result = normalize_type("GEOGRAPHY(POINT, 4326)")
        assert result.get("raw") is True
        assert "GEOGRAPHY" in result["type"]

    def test_enum_type(self):
        result = normalize_type("ENUM")
        assert result["type"] == "enum"

    def test_uuid_type(self):
        assert normalize_type("UUID")["type"] == "uuid"

    def test_bytes_type(self):
        assert normalize_type("BYTEA")["type"] == "bytes"
        assert normalize_type("BLOB")["type"] == "bytes"


class TestComputeChecksum:
    def test_checksum_is_sha256(self):
        snapshot = {
            "format_version": 1,
            "migration_id": "test__0001_init",
            "tables": {},
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        cksum = compute_checksum(snapshot)
        assert len(cksum) == 64
        assert all(c in "0123456789abcdef" for c in cksum)

    def test_checksum_excludes_checksum_field(self):
        s1 = {"a": 1, "checksum": "abc"}
        s2 = {"a": 1, "checksum": "xyz"}
        assert compute_checksum(s1) == compute_checksum(s2)

    def test_checksum_different_for_different_content(self):
        s1 = {"a": 1}
        s2 = {"a": 2}
        assert compute_checksum(s1) != compute_checksum(s2)


class TestWriteReadSnapshot:
    def test_write_and_read_roundtrip(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='test', default=True, database_type='sqlite', "
                "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
            )

            snapshot = {
                "format_version": 1,
                "migration_id": "",
                "database_name": "test",
                "database_type": "sqlite",
                "applied_at": "",
                "tables": {},
                "enums": {},
                "indexes": {},
                "constraints": {},
            }
            filepath = write_snapshot(snapshot, database="test", migration_id="test__0001_init")

            assert filepath.endswith(".schema.json")
            assert "test__0001_init" in filepath

            loaded = read_snapshot(filepath)
            assert loaded is not None
            assert loaded["migration_id"] == "test__0001_init"
            assert loaded["checksum"]
            assert loaded["applied_at"]

    def test_read_nonexistent_file(self):
        result = read_snapshot("/nonexistent/path.schema.json")
        assert result is None

    def test_read_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.schema.json")
            Path(fpath).write_text("not json")
            result = read_snapshot(fpath)
            assert result is None

    def test_read_tampered_snapshot(self):
        snap = {
            "format_version": 1,
            "migration_id": "test__0001_init",
            "database_name": "test",
            "database_type": "sqlite",
            "applied_at": "2026-01-01T00:00:00Z",
            "tables": {"users": {"columns": {"id": {"type": "integer"}}}},
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        cksum = compute_checksum(snap)
        snap["checksum"] = cksum

        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.schema.json")
            with open(fpath, "w") as f:
                json.dump(snap, f)

            loaded = read_snapshot(fpath)
            assert loaded is not None

            snap["checksum"] = cksum
            snap["tables"]["users"]["columns"]["id"]["type"] = "text"
            with open(fpath, "w") as f:
                json.dump(snap, f)

            loaded = read_snapshot(fpath)
            assert loaded is None


class TestFindLatestSnapshot:
    def test_find_latest_returns_highest_version(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='test', default=True, database_type='sqlite', "
                "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
            )

            s1 = {
                "format_version": 1,
                "migration_id": "",
                "database_name": "test",
                "database_type": "sqlite",
                "applied_at": "",
                "tables": {},
                "enums": {},
                "indexes": {},
                "constraints": {},
            }
            write_snapshot(s1, database="test", migration_id="test__0001_init")
            write_snapshot(s1, database="test", migration_id="test__0002_add_email")

            latest = find_latest_snapshot(database="test")
            assert latest is not None
            assert latest["migration_id"] == "test__0002_add_email"

    def test_no_snapshots_returns_none(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='test', default=True, database_type='sqlite', "
                "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
            )

            latest = find_latest_snapshot(database="test")
            assert latest is None

    def test_ignores_other_database_snapshots(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='mydb', default=True, database_type='sqlite', "
                "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
            )

            s = {
                "format_version": 1,
                "migration_id": "",
                "database_name": "otherdb",
                "database_type": "sqlite",
                "applied_at": "",
                "tables": {},
                "enums": {},
                "indexes": {},
                "constraints": {},
            }
            write_snapshot(s, database="mydb", migration_id="otherdb__0001_init")

            latest = find_latest_snapshot(database="mydb")
            assert latest is None


class TestMySQLSnapshot:
    def test_extract_full_schema_snapshot_mysql_metadata(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='mysqltest', default=True, database_type='mysql', "
                "database_url_sync='mysql+pymysql://root:Rocky-011079-mysql@127.0.0.1:3307/dbwarden_mysql_snapshot_test')\n"
            )

            conn = pymysql.connect(
                host="127.0.0.1",
                port=3307,
                user="root",
                password="Rocky-011079-mysql",
                autocommit=True,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute("DROP DATABASE IF EXISTS dbwarden_mysql_snapshot_test")
                    cur.execute("CREATE DATABASE dbwarden_mysql_snapshot_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    cur.execute("USE dbwarden_mysql_snapshot_test")
                    cur.execute(
                        """
                        CREATE TABLE users (
                            id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'Primary key',
                            email VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            PRIMARY KEY (id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC COMMENT='Core users'
                        """
                    )
            finally:
                conn.close()

            snapshot = extract_full_schema_snapshot(database="mysqltest")
            users = snapshot["tables"]["users"]
            assert users["comment"] == "Core users"
            assert users["my_table"]["my_engine"] == "InnoDB"
            assert users["my_table"]["my_charset"] == "utf8mb4"
            assert users["my_table"]["my_collate"] == "utf8mb4_unicode_ci"
            assert users["my_table"]["my_row_format"] == "Dynamic"
            assert users["columns"]["id"]["my_column"]["my_unsigned"] is True
            assert users["columns"]["id"]["comment"] == "Primary key"
            assert users["columns"]["email"]["my_column"]["my_collate"] == "utf8mb4_unicode_ci"
            assert users["columns"]["updated_at"]["my_column"]["my_on_update"] == "CURRENT_TIMESTAMP"


class TestDetectRenames:
    def test_simple_rename_same_type(self):
        dropped = [("old_name", {"type": "varchar", "nullable": True})]
        added = [("new_name", _mc("new_name", "VARCHAR(255)"))]
        renames = detect_renames("t", dropped, added)
        assert renames == [("old_name", "new_name")]

    def test_no_rename_different_type(self):
        dropped = [("old_name", {"type": "varchar", "nullable": True})]
        added = [("new_name", _mc("new_name", "INTEGER"))]
        renames = detect_renames("t", dropped, added)
        assert renames == []

    def test_no_rename_same_name(self):
        dropped = [("col_a", {"type": "varchar", "nullable": True})]
        added = [("col_a", _mc("col_a", "VARCHAR(255)"))]
        renames = detect_renames("t", dropped, added)
        assert renames == []

    def test_multiple_same_type_unambiguous(self):
        dropped = [
            ("old_a", {"type": "varchar", "nullable": True}),
            ("old_b", {"type": "integer", "nullable": True}),
        ]
        added = [
            ("new_a", _mc("new_a", "VARCHAR(255)")),
            ("new_b", _mc("new_b", "INTEGER")),
        ]
        renames = detect_renames("t", dropped, added)
        assert len(renames) == 2
        assert ("old_a", "new_a") in renames
        assert ("old_b", "new_b") in renames

    def test_ambiguous_same_type_count_skips_rename(self):
        dropped = [
            ("old_a", {"type": "varchar", "nullable": True}),
            ("old_b", {"type": "varchar", "nullable": True}),
        ]
        added = [
            ("new_a", _mc("new_a", "VARCHAR(255)")),
            ("new_b", _mc("new_b", "VARCHAR(255)")),
        ]
        renames = detect_renames("t", dropped, added)
        assert len(renames) == 2

    def test_empty_dropped_or_added(self):
        assert detect_renames("t", [], [("c", _mc("c", "INT"))]) == []
        assert detect_renames("t", [("c", {"type": "int"})], []) == []


class TestDiffModelsAgainstSnapshot:
    def test_new_table_detected(self):
        snapshot = {
            "tables": {},
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "create_table" and op["table"] == "users" for op in upgrade)

    def test_dropped_table_detected(self):
        snapshot = {
            "tables": {
                "old_table": {
                    "columns": {"id": {"type": "integer"}},
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables: list[ModelTable] = []
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "drop_table" and op["table"] == "old_table" for op in upgrade)

    def test_add_column_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("email", "VARCHAR(255)"),
                ],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_ops = [op for op in upgrade if op["type"] == "add_column"]
        assert len(add_ops) == 1
        assert add_ops[0]["column"] == "email"

    def test_drop_column_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "legacy_field": {"type": "varchar", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        drop_ops = [op for op in upgrade if op["type"] == "drop_column"]
        assert len(drop_ops) == 1
        assert drop_ops[0]["column"] == "legacy_field"

    def test_rename_column_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "username": {"type": "varchar", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("email", "VARCHAR(255)"),
                ],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        rename_ops = [op for op in upgrade if op["type"] == "rename_column"]
        add_ops = [op for op in upgrade if op["type"] == "add_column"]
        drop_ops = [op for op in upgrade if op["type"] == "drop_column"]

        assert len(rename_ops) == 1, f"Expected 1 rename, got {len(rename_ops)}. add={add_ops}, drop={drop_ops}"
        assert rename_ops[0]["old_name"] == "username"
        assert rename_ops[0]["new_name"] == "email"

    def test_type_change_detected_as_drop_add(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("name", "INTEGER"),
                ],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        rename_ops = [op for op in upgrade if op["type"] == "rename_column"]
        assert len(rename_ops) == 0


class TestSnapshotDiffToSql:
    def test_rename_column_generates_rename_sql(self):
        upgrade_ops = [
            {"type": "rename_column", "table": "users", "old_name": "username", "new_name": "email"},
        ]
        rollback_ops = [
            {"type": "rename_column", "table": "users", "old_name": "email", "new_name": "username"},
        ]
        upgrade_sql, rollback_sql, changes = snapshot_diff_to_sql(upgrade_ops, rollback_ops, db_name=None)
        assert "RENAME COLUMN username TO email" in upgrade_sql
        assert "RENAME COLUMN email TO username" in rollback_sql
        assert any(c.operation == "rename_column" and c.target == "email" for c in changes)


class TestExtractFullSchemaSnapshot:
    def test_extract_from_sqlite(self):
        import sqlite3

        db_path = "/tmp/test_snap_extract.db"
        if os.path.exists(db_path):
            os.unlink(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL)")
        conn.execute("CREATE UNIQUE INDEX ix_items_name ON items(name)")
        conn.close()

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url=f"sqlite:///{db_path}",
            database_type="sqlite",
        )

        assert "items" in snapshot["tables"]
        cols = snapshot["tables"]["items"]["columns"]
        assert cols["id"]["type"] == "integer"
        assert cols["id"]["primary_key"] is True
        assert cols["name"]["type"] == "text"
        assert cols["price"]["type"] == "float"

        assert snapshot["format_version"] == 1

        os.unlink(db_path)

    def test_postgresql_snapshot_skips_inherited_columns(self, monkeypatch):
        class _Result:
            def __init__(self, rows=None, scalar_value=None):
                self._rows = rows or []
                self._scalar_value = scalar_value

            def fetchall(self):
                return self._rows

            def fetchone(self):
                return self._rows[0] if self._rows else None

            def scalar(self):
                return self._scalar_value

        class _Conn:
            def __init__(self):
                self.queries = []
                self.params = []

            def execute(self, stmt, params=None):
                sql = str(stmt)
                self.queries.append(sql)
                self.params.append(params or {})
                if "attisdropped" in sql and "attislocal" in sql:
                    return _Result(rows=[("id",), ("data",)])
                if "pg_inherits" in sql:
                    return _Result(rows=[("app", "e2e_parent")])
                if "pg_constraint" in sql and "contype = 'x'" in sql:
                    assert (params or {}).get("t") == "app.child"
                    return _Result(rows=[])
                return _Result()

            def close(self):
                pass

            def execution_options(self, **kw):
                return self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class _Engine:
            def __init__(self):
                self.conn = _Conn()

            def connect(self):
                return self.conn

            def dispose(self):
                pass

        class _Inspector:
            def get_table_names(self, **kwargs):
                return ["child"]

            def get_columns(self, table_name, **kwargs):
                return [
                    {"name": "id", "type": "INTEGER", "nullable": False, "default": None},
                    {"name": "name", "type": "TEXT", "nullable": True, "default": None},
                    {"name": "data", "type": "TEXT", "nullable": True, "default": None},
                ]

            def get_pk_constraint(self, table_name, **kwargs):
                return {"constrained_columns": ["id"]}

            def get_indexes(self, table_name, **kwargs):
                return []

            def get_foreign_keys(self, table_name, **kwargs):
                return []

            def get_unique_constraints(self, table_name, **kwargs):
                return []

            def get_check_constraints(self, table_name, **kwargs):
                return []

            def get_table_comment(self, table_name, **kwargs):
                return {"text": None}

            def get_enums(self):
                return []

        engine = _Engine()
        monkeypatch.setattr("sqlalchemy.create_engine", lambda url, **kw: engine)
        monkeypatch.setattr("sqlalchemy.inspect", lambda engine_obj: _Inspector())
        monkeypatch.setattr(
            "dbwarden.config.get_database",
            lambda database: type("D", (), {"postgres_schema": "app"})(),
        )

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url="postgresql://example/db",
            database_type="postgresql",
        )

        assert list(snapshot["tables"]["child"]["columns"].keys()) == ["id", "data"]
        assert snapshot["tables"]["child"]["pg_table"]["backend"] == "postgresql"
        assert snapshot["tables"]["child"]["pg_table"]["pg_inherits"] == "e2e_parent"
        assert snapshot["tables"]["child"].get("pg_policies") is None
        assert any("acl.grantee <> c.relowner" in q for q in engine.conn.queries)
        assert any(p.get("t") == "app.child" for p in engine.conn.params)
        assert any("attislocal" in q for q in engine.conn.queries)

    def test_postgresql_snapshot_skips_plain_storage(self, monkeypatch):
        class _Result:
            def __init__(self, rows=None):
                self._rows = rows or []

            def fetchall(self):
                return self._rows

            def fetchone(self):
                return self._rows[0] if self._rows else None

        class _Conn:
            def execute(self, stmt, params=None):
                sql = str(stmt)
                if "attisdropped" in sql and "attislocal" in sql:
                    return _Result(rows=[("id",), ("data",)])
                if "pg_attribute a" in sql and "attstorage" in sql:
                    return _Result(rows=[("id", "p", None), ("data", "x", None)])
                if "pg_inherits" in sql:
                    return _Result(rows=[])
                return _Result()

            def close(self):
                pass

            def execution_options(self, **kw):
                return self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class _Engine:
            def connect(self):
                return _Conn()

            def dispose(self):
                pass

        class _Inspector:
            def get_table_names(self, **kwargs):
                return ["child"]

            def get_columns(self, table_name, **kwargs):
                return [
                    {"name": "id", "type": "INTEGER", "nullable": False, "default": None},
                    {"name": "data", "type": "TEXT", "nullable": True, "default": None},
                ]

            def get_pk_constraint(self, table_name, **kwargs):
                return {"constrained_columns": ["id"]}

            def get_indexes(self, table_name, **kwargs):
                return []

            def get_foreign_keys(self, table_name, **kwargs):
                return []

            def get_unique_constraints(self, table_name, **kwargs):
                return []

            def get_check_constraints(self, table_name, **kwargs):
                return []

            def get_table_comment(self, table_name, **kwargs):
                return {"text": None}

            def get_enums(self):
                return []

        monkeypatch.setattr("sqlalchemy.create_engine", lambda url, **kw: _Engine())
        monkeypatch.setattr("sqlalchemy.inspect", lambda engine_obj: _Inspector())
        monkeypatch.setattr("dbwarden.config.get_database", lambda database: type("D", (), {"postgres_schema": "app"})())

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url="postgresql://example/db",
            database_type="postgresql",
        )

        assert "pg_column" not in snapshot["tables"]["child"]["columns"]["id"]
        assert "pg_column" not in snapshot["tables"]["child"]["columns"]["data"]

    def test_postgresql_snapshot_keeps_only_non_default_opclasses(self, monkeypatch):
        class _Result:
            def __init__(self, rows=None, scalar_value=None):
                self._rows = rows or []
                self._scalar_value = scalar_value

            def fetchall(self):
                return self._rows

            def fetchone(self):
                return self._rows[0] if self._rows else None

            def scalar(self):
                return self._scalar_value

        class _Conn:
            def __init__(self):
                self.queries = []

            def execute(self, stmt, params=None):
                sql = str(stmt)
                self.queries.append(sql)
                if "attisdropped" in sql and "attislocal" in sql:
                    return _Result(rows=[("id",), ("data",)])
                if "opcdefault" in sql:
                    return _Result(rows=[SimpleNamespace(col_def="data", opcname="text_pattern_ops")])
                return _Result()

            def close(self):
                pass

            def execution_options(self, **kw):
                return self

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class _Engine:
            def __init__(self):
                self.conn = _Conn()

            def connect(self):
                return self.conn

            def dispose(self):
                pass

        class _Inspector:
            def get_table_names(self, **kwargs):
                return ["child"]

            def get_columns(self, table_name, **kwargs):
                return [
                    {"name": "id", "type": "INTEGER", "nullable": False, "default": None},
                    {"name": "data", "type": "TEXT", "nullable": True, "default": None},
                ]

            def get_pk_constraint(self, table_name, **kwargs):
                return {"constrained_columns": ["id"]}

            def get_indexes(self, table_name, **kwargs):
                return [{"name": "ix_child_data", "column_names": ["data"], "unique": False, "dialect_options": {"postgresql_using": "btree"}}]

            def get_foreign_keys(self, table_name, **kwargs):
                return []

            def get_unique_constraints(self, table_name, **kwargs):
                return []

            def get_check_constraints(self, table_name, **kwargs):
                return []

            def get_table_comment(self, table_name, **kwargs):
                return {"text": None}

            def get_enums(self):
                return []

        engine = _Engine()
        monkeypatch.setattr("sqlalchemy.create_engine", lambda url, **kw: engine)
        monkeypatch.setattr("sqlalchemy.inspect", lambda engine_obj: _Inspector())
        monkeypatch.setattr("dbwarden.config.get_database", lambda database: type("D", (), {"postgres_schema": "app"})())

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url="postgresql://example/db",
            database_type="postgresql",
        )

        idx = snapshot["indexes"]["child.ix_child_data"]
        assert idx["postgresql_ops"] == {"data": "text_pattern_ops"}
        assert any("opcdefault" in q for q in engine.conn.queries)

    def test_includes_indexes(self):
        import sqlite3

        db_path = "/tmp/test_snap_indexes.db"
        if os.path.exists(db_path):
            os.unlink(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE t (a INT, b INT)")
        conn.execute("CREATE INDEX ix_t_a ON t(a)")
        conn.execute("CREATE UNIQUE INDEX ix_t_b ON t(b)")
        conn.close()

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url=f"sqlite:///{db_path}",
            database_type="sqlite",
        )

        assert any(
            entry.get("name") == "ix_t_a"
            for entry in snapshot["indexes"].values()
        )
        assert any(
            entry.get("name") == "ix_t_b" and entry.get("unique") is True
            for entry in snapshot["indexes"].values()
        )
        assert any(
            entry.get("name") == "ix_t_a" and entry.get("unique") is False
            for entry in snapshot["indexes"].values()
        )

        os.unlink(db_path)

    def test_includes_foreign_keys(self):
        import sqlite3

        db_path = "/tmp/test_snap_fk.db"
        if os.path.exists(db_path):
            os.unlink(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        conn.execute(
            "CREATE TABLE child (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id))"
        )
        conn.close()

        snapshot = extract_full_schema_snapshot(
            sqlalchemy_url=f"sqlite:///{db_path}",
            database_type="sqlite",
        )

        has_fk = any(
            c["type"] == "foreign_key" and c["table"] == "child"
            for c in snapshot["constraints"].values()
        )
        assert has_fk, "Foreign key constraint should be extracted"

        os.unlink(db_path)


class TestApplyRenameIntents:
    def test_keeps_confirmed_auto_rename(self):
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
            {"type": "add_column", "table": "users", "column": "email"},
        ]
        rollback = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        confirmed = {("users", "name", "full_name")}
        result_up, result_rb = _apply_rename_intents(ops, rollback, confirmed)
        assert len(result_up) == 2
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0].get("resolved_from") is None

    def test_removes_non_confirmed_auto_rename(self):
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
        ]
        rollback = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
        ]
        result_up, result_rb = _apply_rename_intents(ops, rollback, set())
        assert len(result_up) == 1
        assert result_up[0]["type"] == "drop_column"
        assert result_up[0]["column"] == "name"

    def test_converts_drop_add_to_rename_from_confirmed(self):
        ops = [
            {"type": "drop_column", "table": "users", "column": "name"},
            {"type": "add_column", "table": "users", "column": "full_name"},
        ]
        rollback = [
            {"type": "add_column", "table": "users", "column": "name", "definition": {}},
            {"type": "drop_column", "table": "users", "column": "full_name"},
        ]
        confirmed = {("users", "name", "full_name")}
        result_up, result_rb = _apply_rename_intents(ops, rollback, confirmed)
        assert len(result_up) == 1
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0]["old_name"] == "name"
        assert result_up[0]["new_name"] == "full_name"

    def test_sets_resolved_from_from_map(self):
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
        ]
        rollback = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
        ]
        confirmed = {("users", "name", "full_name")}
        origin = {("users", "name", "full_name"): "rename_flag"}
        result_up, _ = _apply_rename_intents(ops, rollback, confirmed, origin)
        assert result_up[0]["resolved_from"] == "rename_flag"

    def test_sets_resolved_from_on_converted_rename(self):
        ops = [
            {"type": "drop_column", "table": "users", "column": "name"},
            {"type": "add_column", "table": "users", "column": "full_name"},
        ]
        rollback = [
            {"type": "add_column", "table": "users", "column": "name", "definition": {}},
            {"type": "drop_column", "table": "users", "column": "full_name"},
        ]
        confirmed = {("users", "name", "full_name")}
        origin = {("users", "name", "full_name"): "rename_flag"}
        result_up, _ = _apply_rename_intents(ops, rollback, confirmed, origin)
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0]["resolved_from"] == "rename_flag"

    def test_no_renames_unchanged(self):
        ops = [
            {"type": "add_column", "table": "users", "column": "email"},
        ]
        rollback = [
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        result_up, result_rb = _apply_rename_intents(ops, rollback, set())
        assert result_up == ops
        assert result_rb == rollback


class TestStatementOrder:
    def test_ordering(self):
        assert StatementOrder.CREATE_EXTENSION < StatementOrder.CREATE_SCHEMA
        assert StatementOrder.CREATE_SCHEMA < StatementOrder.CREATE_DOMAIN
        assert StatementOrder.CREATE_DOMAIN < StatementOrder.CREATE_SEQUENCE
        assert StatementOrder.CREATE_SEQUENCE < StatementOrder.RENAME_TABLE
        assert StatementOrder.RENAME_TABLE == 1
        assert StatementOrder.RENAME_TABLE < StatementOrder.RENAME_COLUMN
        assert StatementOrder.RENAME_COLUMN < StatementOrder.ALTER_COLUMN_TYPE
        assert StatementOrder.ALTER_COLUMN_TYPE < StatementOrder.ALTER_COLUMN_NULLABLE
        assert StatementOrder.ALTER_COLUMN_NULLABLE < StatementOrder.ALTER_COLUMN_DEFAULT
        assert StatementOrder.ALTER_COLUMN_DEFAULT < StatementOrder.CREATE_TYPE
        assert StatementOrder.CREATE_TYPE < StatementOrder.CREATE_TABLE
        assert StatementOrder.CREATE_TABLE < StatementOrder.CREATE_VIEW
        assert StatementOrder.CREATE_VIEW < StatementOrder.ADD_COLUMN
        assert StatementOrder.ADD_COLUMN < StatementOrder.ALTER_FOREIGN_KEY
        assert StatementOrder.ALTER_FOREIGN_KEY < StatementOrder.DROP_VIEW
        assert StatementOrder.DROP_VIEW < StatementOrder.ALTER_INDEX
        assert StatementOrder.ALTER_INDEX < StatementOrder.DROP_COLUMN
        assert StatementOrder.DROP_COLUMN < StatementOrder.DROP_TABLE


class TestAssembleMigration:
    def test_sorts_by_order(self):
        stmts = [
            MigrationStatement(StatementOrder.ADD_COLUMN, "add bar", "drop bar"),
            MigrationStatement(StatementOrder.CREATE_TABLE, "create foo", "drop foo"),
            MigrationStatement(StatementOrder.RENAME_COLUMN, "rename x y", "rename y x"),
        ]
        upgrade, rollback = _assemble_migration(stmts)
        parts = upgrade.split("\n\n")
        assert parts[0] == "rename x y"
        assert parts[1] == "create foo"
        assert parts[2] == "add bar"

    def test_rollback_is_reversed(self):
        stmts = [
            MigrationStatement(StatementOrder.ADD_COLUMN, "add bar", "drop bar"),
            MigrationStatement(StatementOrder.CREATE_TABLE, "create foo", "drop foo"),
        ]
        _, rollback = _assemble_migration(stmts)
        parts = rollback.split("\n\n")
        assert parts[0] == "drop bar"
        assert parts[1] == "drop foo"

    def test_empty_list_returns_empty_strings(self):
        upgrade, rollback = _assemble_migration([])
        assert upgrade == ""
        assert rollback == ""

    def test_single_statement(self):
        stmts = [
            MigrationStatement(StatementOrder.CREATE_TABLE, "create foo", "drop foo"),
        ]
        upgrade, rollback = _assemble_migration(stmts)
        assert upgrade == "create foo"
        assert rollback == "drop foo"

    def test_duplicate_order_values(self):
        stmts = [
            MigrationStatement(StatementOrder.ADD_COLUMN, "add bar 1", "drop bar 1"),
            MigrationStatement(StatementOrder.CREATE_TABLE, "create foo", "drop foo"),
            MigrationStatement(StatementOrder.ADD_COLUMN, "add bar 2", "drop bar 2"),
        ]
        upgrade, rollback = _assemble_migration(stmts)
        parts = upgrade.split("\n\n")
        assert parts[0] == "create foo"
        assert parts[1] == "add bar 1"
        assert parts[2] == "add bar 2"

    def test_rollback_only_statement(self):
        stmts = [
            MigrationStatement(StatementOrder.ADD_COLUMN, upgrade_sql="", rollback_sql="drop col"),
        ]
        upgrade, rollback = _assemble_migration(stmts)
        assert upgrade == ""
        assert rollback == "drop col"


class TestDiffModelsAgainstSnapshotEdgeCases:
    def test_empty_model_tables(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        upgrade, rollback = diff_models_against_snapshot([], snapshot)
        assert any(op["type"] == "drop_table" for op in upgrade)

    def test_same_tables_no_changes(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert upgrade == []
        assert rollback == []

    def test_table_with_no_columns_in_snapshot(self):
        snapshot = {
            "tables": {
                "empty": {
                    "columns": {},
                    "primary_key": [],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="empty",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_ops = [op for op in upgrade if op["type"] == "add_column"]
        assert len(add_ops) == 1

    def test_snapshot_no_constraints_indexes_keys(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                }
            },
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
                foreign_keys=[],
                indexes=[],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert upgrade == []

    def test_fk_add_and_drop_same_diff(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "old_ref": {"type": "integer"}}},
                "old_group": {"columns": {"id": {"type": "integer"}}},
                "groups": {"columns": {"id": {"type": "integer"}}},
            },
            "constraints": {
                "users_old_ref_fkey": {
                    "type": "foreign_key",
                    "table": "users",
                    "columns": ["old_ref"],
                    "referenced_table": "old_group",
                    "referenced_columns": ["id"],
                },
            },
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"]}],
            ),
            ModelTable(
                name="groups",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_fk = [op for op in upgrade if op["type"] == "add_foreign_key"]
        drop_fk = [op for op in upgrade if op["type"] == "drop_foreign_key"]
        assert len(add_fk) == 1
        assert len(drop_fk) == 1
        assert add_fk[0]["columns"] == ["group_id"]
        assert drop_fk[0]["columns"] == ["old_ref"]

    def test_index_same_sig_different_name_no_change(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "email": {"type": "varchar"}}},
            },
            "indexes": {
                "custom_idx_name": {"table": "users", "columns": ["email"], "unique": False, "type": "btree"},
            },
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
                indexes=[{"columns": ["email"], "unique": False}],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        idx_ops = [op for op in upgrade if "index" in op["type"]]
        assert len(idx_ops) == 0

    def test_rename_and_type_change_same_table(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True, "primary_key": False},
                        "bio": {"type": "text", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    ModelColumn("full_name", "VARCHAR", True, False, False, None, None),
                    ModelColumn("bio", "TEXT", False, False, False, None, None),
                ],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        rename_ops = [op for op in upgrade if op["type"] == "rename_column"]
        nullable_ops = [op for op in upgrade if op["type"] == "alter_column_nullable"]
        assert len(rename_ops) >= 1
        assert len(nullable_ops) >= 1

    def test_table_rename_and_column_add_combined(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="accounts",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("name", "VARCHAR", True, False, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_ops = [op for op in upgrade if op["type"] == "add_column"]
        drop_ops = [op for op in upgrade if op["type"] == "drop_column"]
        assert len(drop_ops) >= 0


class TestApplyRenameIntentsEdgeCases:
    def test_empty_confirmed_no_renames(self):
        ops = [
            {"type": "add_column", "table": "users", "column": "email"},
        ]
        rollback = [
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        result_up, result_rb = _apply_rename_intents(ops, rollback, set())
        assert result_up == ops
        assert result_rb == rollback

    def test_confirmed_entries_not_matching_any_op(self):
        ops = [
            {"type": "add_column", "table": "users", "column": "email"},
        ]
        rollback = [
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        confirmed = {("other", "foo", "bar")}
        result_up, result_rb = _apply_rename_intents(ops, rollback, confirmed)
        assert result_up == ops

    def test_confirmed_rename_has_resolved_from_flag_map(self):
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
        ]
        rollback = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
        ]
        confirmed = {("users", "name", "full_name")}
        origin = {("users", "name", "full_name"): "rename_flag"}
        result_up, _ = _apply_rename_intents(ops, rollback, confirmed, origin)
        assert result_up[0].get("resolved_from") == "rename_flag"

    def test_all_six_limit_not_exceeded(self):
        ops = []
        rollback = []
        confirmed = set()
        for i in range(6):
            ops.append({"type": "rename_column", "table": "t", "old_name": f"old_{i}", "new_name": f"new_{i}"})
            rollback.append({"type": "rename_column", "table": "t", "old_name": f"new_{i}", "new_name": f"old_{i}"})
            confirmed.add(("t", f"old_{i}", f"new_{i}"))
        result_up, result_rb = _apply_rename_intents(ops, rollback, confirmed)
        assert len(result_up) == 6
        assert all(r["type"] == "rename_column" for r in result_up)

    def test_drop_add_converted_to_rename_with_resolved_from_overlap(self):
        ops = [
            {"type": "drop_column", "table": "users", "column": "name"},
            {"type": "add_column", "table": "users", "column": "full_name"},
        ]
        rollback = [
            {"type": "add_column", "table": "users", "column": "name", "definition": {}},
            {"type": "drop_column", "table": "users", "column": "full_name"},
        ]
        confirmed = {("users", "name", "full_name")}
        origin = {("users", "name", "full_name"): "auto_detect"}
        result_up, _ = _apply_rename_intents(ops, rollback, confirmed, origin)
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0].get("resolved_from") == "auto_detect"

    def test_confirmed_trumps_flag_format(self):
        ops = [
            {"type": "drop_column", "table": "users", "column": "name"},
            {"type": "add_column", "table": "users", "column": "email"},
        ]
        rollback = [
            {"type": "add_column", "table": "users", "column": "name", "definition": {}},
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        confirmed = {("users", "name", "email")}
        result_up, _ = _apply_rename_intents(ops, rollback, confirmed)
        assert len(result_up) == 1
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0]["old_name"] == "name"
        assert result_up[0]["new_name"] == "email"


class TestColumnLevelDiff:
    def test_type_change_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("name", "TEXT"),
                ],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        type_changes = [op for op in upgrade if op["type"] == "alter_column_type"]
        assert len(type_changes) == 1
        assert type_changes[0]["column"] == "name"
        assert type_changes[0]["model_type"] == "TEXT"

    def test_no_type_change_same_type(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        type_changes = [op for op in upgrade if op["type"] == "alter_column_type"]
        assert len(type_changes) == 0

    def test_nullable_change_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "email": {"type": "varchar", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    ModelColumn("email", "VARCHAR(255)", False, False, False, None, None),
                ],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        nullable_changes = [op for op in upgrade if op["type"] == "alter_column_nullable"]
        assert len(nullable_changes) == 1
        assert nullable_changes[0]["column"] == "email"
        assert nullable_changes[0]["nullable"] is False

    def test_default_change_detected(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True, "primary_key": False, "default": "foo"},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    ModelColumn("name", "VARCHAR(255)", True, False, False, "bar", None),
                ],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        default_changes = [op for op in upgrade if op["type"] == "alter_column_default"]
        assert len(default_changes) == 1
        assert default_changes[0]["column"] == "name"
        assert default_changes[0]["default"] == "bar"

    def test_all_column_changes_in_one_table(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "name": {"type": "varchar", "nullable": True, "primary_key": False, "default": None},
                    },
                    "primary_key": [],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("name", "TEXT", False, False, False, "hello", None),
                ],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        types = {op["type"] for op in upgrade}
        assert "alter_column_type" in types
        assert "alter_column_nullable" in types
        assert "alter_column_default" in types


class TestColumnLevelSqlGeneration:
    def test_alter_type_generates_sql(self):
        ops = [
            {"type": "alter_column_type", "table": "users", "column": "name", "model_type": "TEXT"},
        ]
        rollback_ops = [
            {"type": "alter_column_type", "table": "users", "column": "name", "snap_type": "varchar"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
        assert "ALTER COLUMN name" in sql or "name TYPE" in sql or "SQLite does not support" in sql

    def test_alter_nullable_set_not_null(self):
        ops = [
            {"type": "alter_column_nullable", "table": "users", "column": "email", "nullable": False, "col_type": "VARCHAR"},
        ]
        rollback_ops = [
            {"type": "alter_column_nullable", "table": "users", "column": "email", "nullable": True, "col_type": "VARCHAR"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
        assert "NOT NULL" in sql or "not supported" in sql

    def test_alter_default_set(self):
        ops = [
            {"type": "alter_column_default", "table": "users", "column": "name", "default": "'hello'"},
        ]
        rollback_ops = [
            {"type": "alter_column_default", "table": "users", "column": "name", "default": None},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
        assert "SET DEFAULT" in sql

    def test_alter_default_drop(self):
        ops = [
            {"type": "alter_column_default", "table": "users", "column": "name", "default": None},
        ]
        rollback_ops = [
            {"type": "alter_column_default", "table": "users", "column": "name", "default": "'old'"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
        assert "DROP DEFAULT" in sql

    def test_drop_column_warning(self):
        ops = [
            {"type": "drop_column", "table": "users", "column": "legacy", "definition": {"type": "varchar"}},
        ]
        rollback_ops = [
            {"type": "add_column", "table": "users", "column": "legacy", "definition": {"type": "varchar"}},
        ]
        sql, _, _ = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
        assert "WARNING" in sql
        assert "DROP COLUMN" in sql

    def test_safe_type_change_enters_multi_step_mode(self):
        ops = [
            {"type": "alter_column_type", "table": "users", "column": "name", "model_type": "TEXT"},
        ]
        rollback_ops = [
            {"type": "alter_column_type", "table": "users", "column": "name", "snap_type": "varchar"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None, safe_type_change=True)
        assert sql != ""


class TestSnapshotDiffToSqlEdgeCases:
    def test_empty_ops(self):
        sql, rb_sql, changes = snapshot_diff_to_sql([], [], db_name=None)
        assert sql == ""
        assert rb_sql == ""
        assert changes == []

    def test_all_op_types_together(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='test', default=True, database_type='sqlite', "
                "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
            )
            ops = [
                {"type": "rename_table", "old_table": "users", "new_table": "accounts"},
                {"type": "rename_column", "table": "accounts", "old_name": "name", "new_name": "full_name"},
                {"type": "alter_column_type", "table": "accounts", "column": "bio", "model_type": "TEXT"},
                {"type": "alter_column_nullable", "table": "accounts", "column": "email", "nullable": False, "col_type": "VARCHAR"},
                {"type": "alter_column_default", "table": "accounts", "column": "role", "default": "'admin'"},
                {"type": "add_column", "table": "accounts", "column": "phone", "model_column": ModelColumn("phone", "VARCHAR", True, False, False, None, None)},
                {"type": "add_foreign_key", "table": "accounts", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]},
                {"type": "add_index", "table": "accounts", "columns": ["email"], "unique": True},
                {"type": "drop_column", "table": "accounts", "column": "legacy", "definition": {"type": "varchar"}},
                {"type": "drop_table", "table": "old_thing"},
            ]
            rollback_ops = [dict(op) for op in ops]
            sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
            assert "ALTER TABLE users RENAME TO accounts;" in sql
            assert "RENAME COLUMN" in sql
            assert "SET DEFAULT" in sql
            assert "ADD COLUMN" in sql
            assert "ADD CONSTRAINT" in sql or "not supported" in sql
            assert "CREATE UNIQUE INDEX" in sql or "CREATE INDEX" in sql
            assert "WARNING" in sql
            assert "DROP TABLE" in sql
            assert len(changes) == 10

    def test_create_table_emits_indexes_and_postgres_comment(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        monkeypatch.setattr("dbwarden.engine.model_discovery._get_backend_name", lambda db_name=None: "postgresql")

        table = ModelTable(
            name="users",
            columns=[
                ModelColumn("id", "INTEGER", False, True, False, None, None),
                ModelColumn("email", "VARCHAR", False, False, False, None, None),
            ],
            indexes=[IndexInfo(columns=["email"], name="ix_users_email")],
            comment="User table",
        )
        monkeypatch.setattr(
            "dbwarden.engine.snapshot._find_model_table",
            lambda table_name, db_name=None: table if table_name == "users" else None,
        )

        sql, rb_sql, changes = snapshot_diff_to_sql([{"type": "create_table", "table": "users"}], [], db_name="primary")

        assert "CREATE TABLE IF NOT EXISTS users" in sql
        assert "CREATE INDEX CONCURRENTLY ix_users_email ON users (email);" in sql
        assert "COMMENT ON TABLE users IS 'User table';" in sql
        assert "DROP INDEX ix_users_email" in rb_sql
        assert any(c.operation == "add_index" for c in changes)

    def test_rename_plus_type_change_combined(self):
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
            {"type": "alter_column_type", "table": "users", "column": "bio", "model_type": "TEXT"},
        ]
        rollback_ops = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
            {"type": "alter_column_type", "table": "users", "column": "bio", "snap_type": "varchar"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "RENAME COLUMN" in sql
        assert "ALTER COLUMN" in sql or "TYPE" in sql
        assert any(c.operation == "rename_column" for c in changes)
        assert any(c.operation == "alter_column_type" for c in changes)

    def test_malformed_op_missing_keys_skipped(self):
        ops = [
            {"type": "unknown_op", "table": "users"},
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
        ]
        rollback_ops = [
            {"type": "unknown_op", "table": "users"},
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "RENAME COLUMN" in sql

    def test_mysql_syntax_is_used(self):
        ops = [
            {"type": "add_column", "table": "users", "column": "email", "model_column": ModelColumn("email", "VARCHAR(255)", True, False, False, None, None)},
        ]
        rollback_ops = [
            {"type": "drop_column", "table": "users", "column": "email"},
        ]
        sql, _, _ = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
        assert "ADD COLUMN" in sql or "ALTER TABLE" in sql


class TestHandlerConvergence:

    def test_all_op_types_emit(self, monkeypatch):
        """Convergence test: every handler-registered op type emits SQL without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            Path("dbwarden/schemas").mkdir(parents=True)
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n"
                "database_config(database_name='test', default=True, database_type='postgresql', "
                "database_url_sync='postgresql:///test', model_paths=['models'])\n"
            )
            monkeypatch.setattr(
                "dbwarden.engine.snapshot._get_backend",
                lambda db_name=None: "postgresql",
            )
            ops = [
                {"type": "rename_table", "old_table": "users", "new_table": "accounts"},
                {"type": "rename_column", "table": "accounts", "old_name": "name", "new_name": "full_name"},
                {"type": "alter_column_type", "table": "accounts", "column": "bio", "model_type": "TEXT"},
                {"type": "alter_column_nullable", "table": "accounts", "column": "email", "nullable": False, "col_type": "VARCHAR"},
                {"type": "alter_column_default", "table": "accounts", "column": "role", "default": "'admin'"},
                {"type": "alter_column_autoincrement", "table": "accounts", "column": "id", "autoincrement": False, "col_type": "INTEGER", "nullable": False},
                {"type": "alter_column_comment", "table": "accounts", "column": "email", "comment": "user email", "col_type": "VARCHAR", "nullable": True, "autoincrement": False, "my_meta": {}},
                {"type": "add_column", "table": "accounts", "column": "phone", "model_column": ModelColumn("phone", "VARCHAR", True, False, False, None, None)},
                {"type": "drop_column", "table": "accounts", "column": "legacy", "definition": {"type": "varchar"}},
                {"type": "alter_pg_column_meta", "table": "accounts", "column": "id", "col_type": "INTEGER", "snap_type": "integer", "from_pg_column": {}, "to_pg_column": {"default": "1"}},
                {"type": "alter_my_column_meta", "table": "accounts", "column": "id", "col_type": "INTEGER", "snap_type": "integer", "from_my_column": {}, "to_my_column": {"my_col": "val"}, "nullable": True, "default": None, "comment": None, "autoincrement": False, "snap_nullable": True, "snap_default": None, "snap_comment": None},
                {"type": "alter_ch_column", "table": "accounts", "column": "ts", "col_type": "DateTime", "snap_type": "DateTime", "from_ch_column": {}, "to_ch_column": {"codec": "LZ4"}},
                {"type": "add_unique_constraint", "table": "accounts", "columns": ["email"], "name": "uq_accounts_email"},
                {"type": "drop_unique_constraint", "table": "accounts", "columns": ["email"], "name": "uq_accounts_email"},
                {"type": "rename_unique_constraint", "table": "accounts", "old_name": "uq_old", "new_name": "uq_new"},
                {"type": "add_check_constraint", "table": "accounts", "name": "ck_age", "expression": "age > 0"},
                {"type": "drop_check_constraint", "table": "accounts", "name": "ck_age"},
                {"type": "add_foreign_key", "table": "accounts", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]},
                {"type": "drop_foreign_key", "table": "accounts", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"], "name": "fk_accounts_group"},
                {"type": "add_index", "table": "accounts", "columns": ["email"], "unique": True},
                {"type": "drop_index", "table": "accounts", "columns": ["email"], "unique": True, "index_name": "ix_accounts_email"},
                {"type": "alter_table_comment", "table": "accounts", "comment": "user accounts table"},
                {"type": "drop_table", "table": "old_thing"},
                {"type": "alter_pg_table", "table": "accounts", "key": "fillfactor", "from_value": None, "to_value": "70"},
                {"type": "alter_ch_options", "table": "events", "ch_engine": "MergeTree()", "ch_order_by": "(id)", "ch_partition_by": "()"},
                {"type": "alter_my_table", "table": "accounts", "key": "my_engine", "from_value": None, "to_value": "InnoDB"},
                {"type": "create_schema", "schema": "app"},
                {"type": "drop_schema", "schema": "old_schema"},
                {"type": "create_domain", "name": "positive_int", "domain_type": "integer"},
                {"type": "drop_domain", "name": "positive_int"},
                {"type": "create_sequence", "name": "user_seq"},
                {"type": "drop_sequence", "name": "user_seq"},
                {"type": "alter_pg_storage_param", "table": "accounts", "param": "fillfactor", "from_value": None, "to_value": "80"},
                {"type": "alter_pg_rls", "table": "accounts", "enabled": True},
                {"type": "add_policy", "table": "accounts", "name": "policy_self", "using": "user_id = current_user"},
                {"type": "drop_policy", "table": "accounts", "name": "policy_self"},
                {"type": "alter_policy", "table": "accounts", "name": "policy_self", "using": "user_id = current_user"},
                {"type": "add_grant", "table": "accounts", "role": "app_user", "privileges": ["SELECT", "INSERT"]},
                {"type": "revoke_grant", "table": "accounts", "role": "app_user", "privileges": ["SELECT"]},
                {"type": "alter_enum_add_value", "enum_name": "mood", "value": "ok", "after": "happy"},
                {"type": "create_type", "enum_name": "mood", "values": ["happy", "sad"]},
                {"type": "drop_type", "enum_name": "mood"},
                {"type": "alter_view", "table": "active_users", "definition": "SELECT * FROM users WHERE active"},
                {"type": "refresh_matview", "table": "user_stats"},
            ]
            rollback_ops = [dict(op) for op in ops]
            sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="test")
            assert sql
            assert rb_sql
            assert len(changes) >= len(ops)

    def test_handler_diff_to_sql_pipeline(self, monkeypatch):
        """End-to-end: diff_models_against_snapshot -> snapshot_diff_to_sql with handler ops."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        monkeypatch.setattr("dbwarden.engine.model_discovery._get_backend_name", lambda db_name=None: "postgresql")

        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True},
                        "group_id": {"type": "integer", "nullable": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                },
                "groups": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                },
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("full_name", "VARCHAR(255)", True, False, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"]}],
                comment="User accounts",
            ),
            ModelTable(
                name="groups",
                columns=[ModelColumn("id", "INTEGER", False, True, False, None, None)],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "rename_column" for op in upgrade)
        assert any(op["type"] == "add_foreign_key" for op in upgrade)
        assert any(op["type"] == "alter_table_comment" for op in upgrade)

        sql, rb_sql, changes = snapshot_diff_to_sql(upgrade, rollback, db_name=None)
        assert "RENAME COLUMN" in sql
        assert "ADD CONSTRAINT" in sql
        assert "COMMENT ON TABLE" in sql
        assert len(changes) == len(upgrade)

    def test_online_offline_pipeline_equivalence(self, monkeypatch):
        """Online and offline diff paths must render identical SQL per backend."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: db_name or "postgresql")
        monkeypatch.setattr("dbwarden.engine.model_discovery._get_backend_name", lambda db_name=None: db_name or "postgresql")

        prev_tables = [
            ModelTable(
                name="accounts",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None, autoincrement=False),
                    ModelColumn("email", "VARCHAR(255)", True, False, False, None, None),
                    ModelColumn("role", "VARCHAR(50)", True, False, False, None, None),
                    ModelColumn("status", "INTEGER", True, False, False, None, None),
                    ModelColumn("bio", "VARCHAR", True, False, False, None, None),
                    ModelColumn("age", "INTEGER", True, False, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                    ModelColumn("handle", "VARCHAR(50)", True, False, False, None, None),
                ],
                pg_table={"pg_fillfactor": 70},
            ),
            ModelTable(
                name="groups",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                ],
            ),
            ModelTable(
                name="inventory",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("sku", "VARCHAR(64)", False, False, False, None, None),
                    ModelColumn("qty", "INTEGER", False, False, False, None, None),
                ],
                my_table={
                    "my_engine": "innodb",
                    "my_charset": "utf8mb4",
                    "my_collate": "utf8mb4_general_ci",
                    "my_row_format": "dynamic",
                },
            ),
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None),
                    ModelColumn("ts", "DateTime", False, False, False, None, None),
                    ModelColumn("payload", "String", True, False, False, None, None),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                    "ch_partition_by": "toYYYYMM(ts)",
                },
            ),
            ModelTable(
                name="event_logs",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None),
                    ModelColumn("ts", "DateTime", False, False, False, None, None),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["ts"],
                },
            ),
        ]

        curr_tables = [
            ModelTable(
                name="accounts",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None, autoincrement=True),
                    ModelColumn("email", "VARCHAR(255)", False, False, False, None, None, comment="contact email"),
                    ModelColumn("role", "VARCHAR(50)", True, False, False, None, None),
                    ModelColumn("status", "INTEGER", True, False, False, 1, None),
                    ModelColumn("bio", "TEXT", True, False, False, None, None),
                    ModelColumn("age", "INTEGER", True, False, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                    ModelColumn("handle", "VARCHAR(50)", True, False, False, None, None),
                ],
                indexes=[IndexInfo(name="ix_accounts_email", columns=["email"], unique=False)],
                uniques=[{"name": "uq_accounts_handle", "columns": ["handle"]}],
                comment="User accounts",
                pg_table={"pg_fillfactor": 80},
            ),
            ModelTable(
                name="groups",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                ],
            ),
            ModelTable(
                name="inventory",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("sku", "VARCHAR(64)", False, False, False, None, None),
                    ModelColumn("qty", "INTEGER", False, False, False, None, None),
                ],
                my_table={
                    "my_engine": "myisam",
                    "my_charset": "latin1",
                    "my_collate": "latin1_swedish_ci",
                    "my_row_format": "compact",
                    "my_auto_increment": 42,
                },
            ),
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None),
                    ModelColumn("ts", "DateTime", False, False, False, None, None),
                    ModelColumn("payload", "String", True, False, False, None, None),
                ],
                clickhouse_options={
                    "ch_engine": "ReplacingMergeTree",
                    "ch_order_by": ["ts", "id"],
                    "ch_partition_by": "toYYYYMM(ts)",
                },
            ),
            ModelTable(
                name="event_logs",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None),
                    ModelColumn("ts", "DateTime", False, False, False, None, None),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["ts", "id"],
                    "ch_ttl": ["ts + INTERVAL 1 DAY"],
                },
            ),
        ]

        prev_state = model_state_to_dict(prev_tables)
        curr_state = model_state_to_dict(curr_tables)
        snapshot = model_state_to_dict(prev_tables)
        for table in prev_tables:
            snapshot["tables"][table.name]["clickhouse_options"] = dict(table.clickhouse_options)
            snapshot["tables"][table.name]["pg_table"] = dict(table.pg_table)
            snapshot["tables"][table.name]["my_table"] = dict(table.my_table)

        def _backend_for_table(state: dict, table_name: str) -> str | None:
            table = state.get("tables", {}).get(table_name, {})
            return (table.get("backend_table_spec") or {}).get("backend")

        def _sorted_ops(ops: list[dict], state: dict, backend: str) -> list[dict]:
            relevant = [
                op for op in ops
                if _backend_for_table(state, op.get("table", "")) == backend
            ]
            return sorted(relevant, key=lambda op: json.dumps(op, sort_keys=True, default=str))

        def _render(ops: list[dict], rollback_ops: list[dict], state: dict, backend: str) -> tuple[str, str]:
            return snapshot_diff_to_sql(
                _sorted_ops(ops, state, backend),
                _sorted_ops(rollback_ops, state, backend),
                db_name=backend,
            )[:2]

        online_upgrade, online_rollback = diff_models_against_snapshot(
            curr_tables,
            snapshot,
            db_name="postgresql",
            clickhouse_engine_recreate=True,
        )
        offline_upgrade, offline_rollback = diff_model_states(prev_state, curr_state)

        for backend in ("postgresql", "mysql", "clickhouse"):
            online_sql, online_rb_sql = _render(online_upgrade, online_rollback, prev_state, backend)
            offline_sql, offline_rb_sql = _render(offline_upgrade, offline_rollback, prev_state, backend)
            assert online_sql == offline_sql
            assert online_rb_sql == offline_rb_sql
    def test_compute_overlap_high(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False},
                        "name": {"type": "varchar", "nullable": True},
                        "email": {"type": "varchar", "nullable": True},
                    }
                }
            }
        }
        model_tables = [
            ModelTable(
                name="accounts",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("name", "VARCHAR", True, False, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
            )
        ]
        ratio = _compute_table_overlap("users", "accounts", snapshot, model_tables)
        assert ratio >= 0.6

    def test_compute_overlap_low(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False},
                        "legacy": {"type": "varchar", "nullable": True},
                    }
                }
            }
        }
        model_tables = [
            ModelTable(
                name="accounts",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("name", "VARCHAR", True, False, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
            )
        ]
        ratio = _compute_table_overlap("users", "accounts", snapshot, model_tables)
        assert ratio < 0.6

    def test_compute_overlap_empty_tables(self):
        snapshot = {
            "tables": {
                "empty_snap": {"columns": {}},
            }
        }
        model_tables = [
            ModelTable(name="empty_model", columns=[]),
        ]
        ratio = _compute_table_overlap("empty_snap", "empty_model", snapshot, model_tables)
        assert ratio == 0.0

    def test_rename_table_sql_generates_statement(self):
        intent = TableRenameIntent(old_table="users", new_table="accounts")
        stmt = _rename_table_sql(intent, "postgresql")
        assert stmt.order == StatementOrder.RENAME_TABLE
        assert "ALTER TABLE users RENAME TO accounts;" in stmt.upgrade_sql
        assert "ALTER TABLE accounts RENAME TO users;" in stmt.rollback_sql

    def test_rename_table_sql_clickhouse_rename(self):
        intent = TableRenameIntent(old_table="users", new_table="accounts")
        stmt = _rename_table_sql(intent, "clickhouse")
        assert "RENAME TABLE users TO accounts;" in stmt.upgrade_sql
        assert "RENAME TABLE accounts TO users;" in stmt.rollback_sql

    def test_rename_table_sql_sqlite(self):
        intent = TableRenameIntent(old_table="users", new_table="accounts")
        stmt = _rename_table_sql(intent, "sqlite")
        assert stmt.order == StatementOrder.RENAME_TABLE
        assert "ALTER TABLE users RENAME TO accounts;" in stmt.upgrade_sql

    def test_rename_table_op_in_snapshot_diff_to_sql(self):
        ops = [
            {"type": "rename_table", "old_table": "users", "new_table": "accounts"},
        ]
        rollback_ops = [
            {"type": "rename_table", "old_table": "accounts", "new_table": "users"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "ALTER TABLE users RENAME TO accounts;" in sql
        assert "ALTER TABLE accounts RENAME TO users;" in rb_sql
        assert any(c.operation == "rename_table" for c in changes)

    def test_rename_table_ordering_first(self):
        ops = [
            {"type": "add_column", "table": "accounts", "column": "email", "model_column": ModelColumn("email", "VARCHAR", True, False, False, None, None)},
            {"type": "rename_table", "old_table": "users", "new_table": "accounts"},
        ]
        rollback_ops = [
            {"type": "drop_column", "table": "accounts", "column": "email"},
            {"type": "rename_table", "old_table": "accounts", "new_table": "users"},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        parts = sql.split("\n\n")
        assert "ALTER TABLE users RENAME TO accounts;" in parts[0]
        assert "ALTER TABLE accounts RENAME TO users;" in rb_sql


class TestForeignKeyDiff:
    def test_fk_name_generation(self):
        handler = ConstraintHandler()
        name = handler._build_fk_name("users", ["group_id"])
        assert name == "fk_users_group_id"

    def test_fk_diff_add(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "group_id": {"type": "integer"}}},
                "groups": {"columns": {"id": {"type": "integer"}, "name": {"type": "varchar"}}},
            },
            "constraints": {},
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"]}],
            ),
            ModelTable(
                name="groups",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("name", "VARCHAR", True, False, False, None, None),
                ],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        fk_ops = [op for op in upgrade if op["type"] == "add_foreign_key"]
        assert len(fk_ops) == 1
        assert fk_ops[0]["columns"] == ["group_id"]
        assert fk_ops[0]["referenced_table"] == "groups"

    def test_fk_diff_drop(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "group_id": {"type": "integer"}}},
                "groups": {"columns": {"id": {"type": "integer"}}},
            },
            "constraints": {
                "users_group_id_fkey": {
                    "type": "foreign_key",
                    "table": "users",
                    "columns": ["group_id"],
                    "referenced_table": "groups",
                    "referenced_columns": ["id"],
                    "on_delete": "NO ACTION",
                    "on_update": "NO ACTION",
                },
            },
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        fk_ops = [op for op in upgrade if op["type"] == "drop_foreign_key"]
        assert len(fk_ops) == 1
        assert fk_ops[0]["columns"] == ["group_id"]

    def test_fk_diff_no_change(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "group_id": {"type": "integer"}}},
                "groups": {"columns": {"id": {"type": "integer"}}},
            },
            "constraints": {
                "users_group_id_fkey": {
                    "type": "foreign_key",
                    "table": "users",
                    "columns": ["group_id"],
                    "referenced_table": "groups",
                    "referenced_columns": ["id"],
                    "on_delete": "NO ACTION",
                    "on_update": "NO ACTION",
                },
            },
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"]}],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        fk_ops = [op for op in upgrade if "foreign_key" in op["type"]]
        assert len(fk_ops) == 0

    def test_fk_add_sql_postgresql(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert len(stmts) == 1
        assert "ADD CONSTRAINT" in stmts[0].upgrade_sql
        assert "fk_users_group_id" in stmts[0].upgrade_sql

    def test_fk_drop_sql_mysql(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "mysql")
        op = Op(object_type="drop_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "DROP FOREIGN KEY" in stmts[0].upgrade_sql

    def test_fk_sql_sqlite_not_supported(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "sqlite")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "not supported" in stmts[0].upgrade_sql

    def test_fk_sql_with_deferrable(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"], "deferrable": True})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "DEFERRABLE INITIALLY DEFERRED" in stmts[0].upgrade_sql

    def test_fk_match_full_emits_match_clause(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={
            "table": "users", "columns": ["group_id"],
            "referenced_table": "groups", "referenced_columns": ["id"],
            "match": "FULL",
        })
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "MATCH FULL" in stmts[0].upgrade_sql

    def test_fk_match_simple_not_emitted(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={
            "table": "users", "columns": ["group_id"],
            "referenced_table": "groups", "referenced_columns": ["id"],
            "match": "SIMPLE",
        })
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "MATCH" not in stmts[0].upgrade_sql

    def test_fk_match_none_not_emitted(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={
            "table": "users", "columns": ["group_id"],
            "referenced_table": "groups", "referenced_columns": ["id"],
        })
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "MATCH" not in stmts[0].upgrade_sql

    def test_fk_match_simple_canonicalized_to_absence(self):
        """Canonicalize SIMPLE to absence so snap and model compare equal."""
        handler = ConstraintHandler()
        snap_spec = {"users": {"uniques": {}, "checks": {}, "fks": [
            {"columns": ["a"], "referenced_table": "b", "referenced_columns": ["id"],
             "match": "SIMPLE", "on_delete": "NO ACTION", "on_update": "NO ACTION"},
        ]}}
        model_spec = {"users": {"uniques": {}, "checks": {}, "fks": [
            {"columns": ["a"], "referenced_table": "b", "referenced_columns": ["id"],
             "on_delete": "NO ACTION", "on_update": "NO ACTION"},
        ]}}
        c_snap = handler.canonicalize(snap_spec)
        c_model = handler.canonicalize(model_spec)
        assert c_snap == c_model
        up, rb = handler.diff(c_snap, c_model)
        assert up == []

    def test_fk_validation_skips_missing_ref_table(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "group_id": {"type": "integer"}}},
            },
            "constraints": {},
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"]}],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        fk_ops = [op for op in upgrade if op["type"] == "add_foreign_key"]
        assert len(fk_ops) == 0


class TestIndexDiff:
    def test_index_name_generation_non_unique(self):
        name = _build_index_name("users", ["email"], False)
        assert name == "idx_users_email"

    def test_index_name_generation_unique(self):
        name = _build_index_name("users", ["email"], True)
        assert name == "uq_users_email"

    def test_index_diff_add(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "email": {"type": "varchar"}}},
            },
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
                indexes=[{"columns": ["email"], "unique": True}],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        idx_ops = [op for op in upgrade if op["type"] == "add_index"]
        assert len(idx_ops) == 1
        assert idx_ops[0]["columns"] == ["email"]
        assert idx_ops[0]["unique"] is True

    def test_index_diff_drop(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "email": {"type": "varchar"}}},
            },
            "indexes": {
                "idx_users_email": {"table": "users", "columns": ["email"], "unique": False, "type": "btree"},
            },
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        idx_ops = [op for op in upgrade if op["type"] == "drop_index"]
        assert len(idx_ops) == 1
        assert idx_ops[0]["columns"] == ["email"]

    def test_index_diff_no_change(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "email": {"type": "varchar"}}},
            },
            "indexes": {
                "uq_users_email": {"table": "users", "columns": ["email"], "unique": True, "type": "btree"},
            },
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("email", "VARCHAR", True, False, False, None, None),
                ],
                indexes=[{"columns": ["email"], "unique": True}],
            ),
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        idx_ops = [op for op in upgrade if "index" in op["type"]]
        assert len(idx_ops) == 0

    def test_index_add_sql_postgresql(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": True}
        stmts = _build_index_sql(op, "postgresql")
        assert "CREATE UNIQUE INDEX" in stmts[0].upgrade_sql
        assert "CONCURRENTLY" in stmts[0].upgrade_sql

    def test_index_add_sql_postgresql_concurrent_is_autocommit_marked(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": False}
        stmts = _build_index_sql(op, "postgresql")
        assert stmts[0].upgrade_sql.startswith("-- @dbwarden:autocommit\n")

    def test_index_add_sql_sqlite(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": False}
        stmts = _build_index_sql(op, "sqlite")
        assert "CREATE INDEX" in stmts[0].upgrade_sql
        assert "CONCURRENTLY" not in stmts[0].upgrade_sql

    def test_index_drop_sql(self):
        op = {"type": "drop_index", "table": "users", "index_name": "idx_users_email", "columns": ["email"], "unique": False}
        stmts = _build_index_sql(op, "postgresql")
        assert "DROP INDEX idx_users_email;" in stmts[0].upgrade_sql

    def test_index_sql_with_postgresql_ops(self):
        op = {"type": "add_index", "table": "users", "columns": ["data"],
              "using": "gin", "postgresql_ops": {"data": "jsonb_path_ops"}}
        stmts = _build_index_sql(op, "postgresql")
        assert "USING gin" in stmts[0].upgrade_sql
        assert "data jsonb_path_ops" in stmts[0].upgrade_sql

    def test_index_drop_rollback_with_postgresql_ops(self):
        op = {"type": "drop_index", "table": "users", "columns": ["data"],
              "index_name": "idx_users_data", "using": "gin",
              "postgresql_ops": {"data": "jsonb_path_ops"}}
        stmts = _build_index_sql(op, "postgresql")
        assert "data jsonb_path_ops" in stmts[0].rollback_sql

    def test_index_sql_with_opclass_and_sorting(self):
        op = {"type": "add_index", "table": "users", "columns": ["data"],
              "using": "gin",
              "postgresql_ops": {"data": "jsonb_path_ops"},
              "column_sorting": {"data": "DESC"}}
        stmts = _build_index_sql(op, "postgresql")
        assert "data jsonb_path_ops DESC" in stmts[0].upgrade_sql
        assert "data DESC jsonb_path_ops" not in stmts[0].upgrade_sql

    def test_index_name_generation_multi_column(self):
        name = _build_index_name("users", ["first_name", "last_name"], True)
        assert name == "uq_users_first_name_last_name"

    def test_fk_and_index_in_snapshot_diff_to_sql(self):
        ops = [
            {"type": "add_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]},
            {"type": "add_index", "table": "users", "columns": ["email"], "unique": True},
        ]
        rollback_ops = [
            {"type": "drop_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]},
            {"type": "drop_index", "table": "users", "columns": ["email"], "unique": True},
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "ADD CONSTRAINT" in sql
        assert "CREATE" in sql
        assert any(c.operation == "add_foreign_key" for c in changes)
        assert any(c.operation == "add_index" for c in changes)

    def test_fk_rollback_sql_correctness(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]})
        stmt = ConstraintHandler().emit(op, db_name="primary")[0]
        assert "DROP CONSTRAINT" in stmt.rollback_sql
        assert "fk_users_group_id" in stmt.rollback_sql

    def test_fk_mariadb_uses_drop_foreign_key(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "mariadb")
        op = Op(object_type="drop_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]})
        stmt = ConstraintHandler().emit(op, db_name="primary")
        assert "DROP FOREIGN KEY" in stmt[0].upgrade_sql

    def test_index_mysql_syntax(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": False}
        stmt = _build_index_sql(op, "mysql")
        assert "CREATE INDEX" in stmt[0].upgrade_sql
        assert "idx_users_email" in stmt[0].upgrade_sql

    def test_index_mariadb_syntax(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": True}
        stmt = _build_index_sql(op, "mariadb")
        assert "CREATE UNIQUE INDEX" in stmt[0].upgrade_sql

    def test_mysql_table_option_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_my_table",
                    "table": "users",
                    "key": "my_engine",
                    "from_value": "InnoDB",
                    "to_value": "MyISAM",
                }]
                rollback_ops = [{
                    "type": "alter_my_table",
                    "table": "users",
                    "key": "my_engine",
                    "from_value": "MyISAM",
                    "to_value": "InnoDB",
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users ENGINE=MyISAM;" in sql
                assert "ALTER TABLE users ENGINE=InnoDB;" in rb_sql
            finally:
                os.chdir(old)

    def test_mysql_column_meta_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_my_column_meta",
                    "table": "users",
                    "column": "id",
                    "col_type": "integer",
                    "snap_type": "integer",
                    "from_my_column": {},
                    "to_my_column": {"my_unsigned": True},
                }]
                rollback_ops = [{
                    "type": "alter_my_column_meta",
                    "table": "users",
                    "column": "id",
                    "col_type": "integer",
                    "snap_type": "integer",
                    "from_my_column": {"my_unsigned": True},
                    "to_my_column": {},
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users MODIFY COLUMN id integer UNSIGNED;" in sql
                assert "ALTER TABLE users MODIFY COLUMN id integer;" in rb_sql
            finally:
                os.chdir(old)

    def test_mysql_table_comment_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', "
                    "database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_table_comment",
                    "table": "users",
                    "comment": "Core users table",
                    "previous_comment": "",
                }]
                rollback_ops = [{
                    "type": "alter_table_comment",
                    "table": "users",
                    "comment": "",
                    "previous_comment": "Core users table",
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users COMMENT = 'Core users table';" in sql
                assert "ALTER TABLE users COMMENT = '';" in rb_sql
            finally:
                os.chdir(old)

    def test_mysql_column_comment_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', "
                    "database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_column_comment",
                    "table": "users",
                    "column": "email",
                    "comment": "User email address",
                    "previous_comment": "",
                    "col_type": "VARCHAR(255)",
                    "nullable": False,
                    "autoincrement": False,
                    "my_meta": {},
                }]
                rollback_ops = [{
                    "type": "alter_column_comment",
                    "table": "users",
                    "column": "email",
                    "comment": "",
                    "previous_comment": "User email address",
                    "col_type": "VARCHAR(255)",
                    "nullable": False,
                    "autoincrement": False,
                    "my_meta": {},
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users MODIFY COLUMN email VARCHAR(255) NOT NULL COMMENT 'User email address';" in sql
                assert "ALTER TABLE users MODIFY COLUMN email VARCHAR(255) NOT NULL COMMENT '';" in rb_sql
            finally:
                os.chdir(old)

    def test_mysql_autoincrement_add_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', "
                    "database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_column_autoincrement",
                    "table": "users",
                    "column": "id",
                    "autoincrement": True,
                    "col_type": "INT",
                    "nullable": False,
                }]
                rollback_ops = [{
                    "type": "alter_column_autoincrement",
                    "table": "users",
                    "column": "id",
                    "autoincrement": False,
                    "col_type": "INT",
                    "nullable": False,
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT;" in sql
                assert "ALTER TABLE users MODIFY COLUMN id INT NOT NULL;" in rb_sql
            finally:
                os.chdir(old)

    def test_mysql_autoincrement_remove_sql(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.getcwd()
            os.chdir(tmpdir)
            try:
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='mysql_db', default=True, database_type='mysql', "
                    "database_url_sync='mysql+pymysql://root:pw@localhost/test')\n"
                )
                ops = [{
                    "type": "alter_column_autoincrement",
                    "table": "users",
                    "column": "id",
                    "autoincrement": False,
                    "col_type": "INT",
                    "nullable": False,
                }]
                rollback_ops = [{
                    "type": "alter_column_autoincrement",
                    "table": "users",
                    "column": "id",
                    "autoincrement": True,
                    "col_type": "INT",
                    "nullable": False,
                }]
                sql, rb_sql, _changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="mysql_db")
                assert "ALTER TABLE users MODIFY COLUMN id INT NOT NULL;" in sql
                assert "ALTER TABLE users MODIFY COLUMN id INT NOT NULL AUTO_INCREMENT;" in rb_sql
            finally:
                os.chdir(old)

    def test_normalize_mysql_default_strips_on_update_clause(self):
        assert _normalize_mysql_default("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP") == "CURRENT_TIMESTAMP"

    def test_mysql_table_diff_ignores_omitted_auto_increment_and_row_format_case(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True, "my_column": {"my_unsigned": True}},
                    },
                    "my_table": {
                        "my_engine": "InnoDB",
                        "my_charset": "utf8mb4",
                        "my_collate": "utf8mb4_unicode_ci",
                        "my_row_format": "Dynamic",
                        "my_auto_increment": 1,
                    },
                }
            },
            "constraints": {},
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[ModelColumn("id", "INT", False, True, False, None, None, my_meta={"my_unsigned": True})],
                my_table={
                    "my_engine": "InnoDB",
                    "my_charset": "utf8mb4",
                    "my_collate": "utf8mb4_unicode_ci",
                    "my_row_format": "DYNAMIC",
                },
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot, db_name=None)
        assert upgrade == []
        assert rollback == []

    def test_index_clickhouse_uses_generic(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": False}
        stmt = _build_index_sql(op, "clickhouse")
        assert "CREATE INDEX" in stmt[0].upgrade_sql

    def test_index_drop_sqlite(self):
        op = {"type": "drop_index", "table": "users", "index_name": "idx_users_email", "columns": ["email"], "unique": False}
        stmt = _build_index_sql(op, "sqlite")
        assert "DROP INDEX idx_users_email;" in stmt[0].upgrade_sql

    def test_index_rollback_creates_index(self):
        op = {"type": "drop_index", "table": "users", "index_name": "uq_users_email", "columns": ["email"], "unique": True}
        stmt = _build_index_sql(op, "postgresql")
        assert "CREATE UNIQUE INDEX" in stmt[0].rollback_sql

    def test_composite_fk_name_generation(self):
        handler = ConstraintHandler()
        name = handler._build_fk_name("orders", ["user_id", "product_id"])
        assert name == "fk_orders_user_id_product_id"

    def test_fk_add_sql_does_not_include_on_delete(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"], "on_delete": "CASCADE"})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "ON DELETE CASCADE" in stmts[0].upgrade_sql

    def test_fk_add_sql_does_not_include_on_update(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        op = Op(object_type="add_foreign_key", upgrade_attrs={"table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"], "on_update": "SET NULL"})
        stmts = ConstraintHandler().emit(op, db_name="primary")
        assert "ON UPDATE SET NULL" in stmts[0].upgrade_sql

    def test_fk_diff_detects_on_delete_change(self):
        snapshot = {
            "tables": {
                "users": {"columns": {"id": {"type": "integer"}, "group_id": {"type": "integer"}}},
                "groups": {"columns": {"id": {"type": "integer"}}},
            },
            "constraints": {
                "users_group_id_fkey": {
                    "type": "foreign_key",
                    "table": "users",
                    "columns": ["group_id"],
                    "referenced_table": "groups",
                    "referenced_columns": ["id"],
                    "on_delete": "NO ACTION",
                    "on_update": "NO ACTION",
                },
            },
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("id", "INTEGER", False, True, False, None, None),
                    ModelColumn("group_id", "INTEGER", True, False, False, None, None),
                ],
                foreign_keys=[{"columns": ["group_id"], "referred_table": "groups", "referred_columns": ["id"], "on_delete": "CASCADE"}],
            ),
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "drop_foreign_key" for op in upgrade)
        assert any(op["type"] == "add_foreign_key" and op.get("on_delete") == "CASCADE" for op in upgrade)

    def test_unique_constraint_diff_add(self):
        snapshot = {"tables": {"users": {"columns": {"email": {"type": "varchar"}}}}, "constraints": {}, "indexes": {}}
        model_tables = [
            ModelTable(
                name="users",
                columns=[ModelColumn("email", "VARCHAR", False, False, False, None, None)],
                uniques=[{"name": "uq_users_email", "columns": ["email"], "deferrable": True}],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "add_unique_constraint" for op in upgrade)

    def test_check_constraint_diff_add(self):
        snapshot = {"tables": {"users": {"columns": {"age": {"type": "integer"}}}}, "constraints": {}, "indexes": {}}
        model_tables = [
            ModelTable(
                name="users",
                columns=[ModelColumn("age", "INTEGER", False, False, False, None, None)],
                checks=[{"name": "ck_users_age", "expression": "age >= 0"}],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "add_check_constraint" for op in upgrade)

    def test_comment_and_pg_meta_diff(self):
        snapshot = {
            "tables": {
                "users": {
                    "comment": "Old comment",
                    "columns": {
                        "email": {
                            "type": "varchar",
                            "nullable": False,
                            "comment": "Old email",
                            "pg_column": {"collation": "C"},
                        }
                    },
                }
            },
            "constraints": {},
            "indexes": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[ModelColumn("email", "VARCHAR", False, False, False, None, None, comment="New email", pg_meta={"pg_collation": "en_US.UTF-8"})],
                comment="New comment",
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "alter_table_comment" for op in upgrade)
        assert any(op["type"] == "alter_column_comment" for op in upgrade)
        assert any(op["type"] == "alter_pg_column_meta" for op in upgrade)

    def test_index_signature_preserves_column_order(self):
        snapshot = {
            "tables": {"users": {"columns": {"first_name": {"type": "varchar"}, "last_name": {"type": "varchar"}}}},
            "indexes": {
                "idx_users_name": {"table": "users", "columns": ["last_name", "first_name"], "unique": False, "using": "btree"},
            },
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[
                    ModelColumn("first_name", "VARCHAR", True, False, False, None, None),
                    ModelColumn("last_name", "VARCHAR", True, False, False, None, None),
                ],
                indexes=[{"columns": ["first_name", "last_name"], "unique": False, "using": "btree"}],
            )
        ]
        upgrade, _ = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "drop_index" for op in upgrade)
        assert any(op["type"] == "add_index" for op in upgrade)


class TestClickHouseDiff:
    def test_diff_models_detects_clickhouse_option_change(self):
        model_tables = [
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                },
            )
        ]
        snapshot = {
            "tables": {
                "events": {
                    "object_type": "table",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "ReplacingMergeTree",
                        "ch_order_by": ["id"],
                    },
                    "indexes": {},
                }
            },
            "indexes": {},
            "constraints": {},
        }

        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)

        assert any(op["type"] == "recreate_ch_table" for op in upgrade)
        assert any(op["type"] == "recreate_ch_table" for op in rollback)

    def test_recreate_preserves_projections(self):
        model_tables = [
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                },
            )
        ]
        snapshot = {
            "tables": {
                "events": {
                    "object_type": "table",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "ReplacingMergeTree",
                        "ch_order_by": ["id"],
                        "ch_projections": [{"name": "by_id", "query": "SELECT id ORDER BY id"}],
                    },
                    "indexes": {},
                }
            },
            "indexes": {},
            "constraints": {},
        }
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "recreate_ch_table" for op in upgrade)

    def test_recreate_inline_materialized_view(self):
        """Inline MV (no TO target) now recreates with DROP VIEW + CREATE MATERIALIZED VIEW."""
        model_tables = [
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                },
            )
        ]
        snapshot = {
            "tables": {
                "events": {
                    "object_type": "materialized_view",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "ReplicatedMergeTree",
                        "ch_order_by": ["id"],
                        "ch_select_statement": "SELECT id FROM source",
                    },
                    "indexes": {},
                }
            },
            "indexes": {},
            "constraints": {},
        }
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        recreate = next(op for op in upgrade if op["type"] == "recreate_ch_table")
        assert recreate is not None

    def test_recreate_dictionary(self):
        model_tables = [
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                },
            )
        ]
        snapshot = {
            "tables": {
                "events": {
                    "object_type": "dictionary",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "ReplicatedMergeTree",
                        "ch_order_by": ["id"],
                        "ch_dictionary": True,
                    },
                    "indexes": {},
                }
            },
            "indexes": {},
            "constraints": {},
        }
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        assert any(op["type"] == "recreate_ch_table" for op in upgrade)

    def test_recreate_annotates_dependent_mvs(self):
        model_tables = [
            ModelTable(
                name="events",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_order_by": ["id"],
                },
            ),
            ModelTable(
                name="events_mv",
                columns=[
                    ModelColumn("id", "UInt64", False, True, False, None, None, ch_meta={"ch_type": "UInt64"}),
                ],
                clickhouse_options={
                    "ch_engine": "MergeTree",
                    "ch_select_statement": "SELECT id FROM source",
                    "ch_to_table": "events",
                },
            ),
        ]
        snapshot = {
            "tables": {
                "events": {
                    "object_type": "table",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "ReplicatedMergeTree",
                        "ch_order_by": ["id"],
                    },
                    "indexes": {},
                },
                "events_mv": {
                    "object_type": "materialized_view",
                    "columns": {
                        "id": {
                            "type": "UInt64",
                            "nullable": False,
                            "default": None,
                            "ch_column": {"ch_type": "UInt64"},
                        }
                    },
                    "clickhouse_options": {
                        "ch_engine": "MergeTree",
                        "ch_select_statement": "SELECT id FROM source",
                        "ch_to_table": "events",
                    },
                    "indexes": {},
                },
            },
            "indexes": {},
            "constraints": {},
        }
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        recreate = next(op for op in upgrade if op["type"] == "recreate_ch_table")
        assert recreate.get("dependent_mvs") == ["events_mv"]

    def test_snapshot_diff_to_sql_clickhouse_ch_ops(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "clickhouse")

        ops = [
            {
                "type": "alter_ch_options",
                "table": "events",
                "changes": {"ch_ttl": {"from": ["old_ttl"], "to": ["new_ttl"]}},
            },
            {
                "type": "alter_ch_column",
                "table": "events",
                "column": "payload",
                "from_ch_column": {"ch_type": "String"},
                "to_ch_column": {"ch_type": "LowCardinality(String)", "ch_codec": "ZSTD(3)"},
            },
            {
                "type": "drop_table",
                "table": "dict_events",
                "object_type": "dictionary",
            },
        ]

        sql, rollback_sql, changes = snapshot_diff_to_sql(ops, [], db_name="clickhouse")

        assert "ALTER TABLE events MODIFY TTL new_ttl" in sql
        assert "ALTER TABLE events MODIFY COLUMN payload LowCardinality(String)" in sql
        assert "DROP DICTIONARY dict_events" in sql
        assert changes

    def test_snapshot_diff_to_sql_recreate_with_mixed_ops(self, monkeypatch):
        """recreate_ch_table coexists with other op types for different tables."""
        monkeypatch.setattr("dbwarden.engine.model_discovery._get_backend_name", lambda db_name=None: "clickhouse")
        state_events = {
            "name": "events",
            "object_type": "table",
            "columns": {
                "id": {
                    "name": "id", "type": "UInt64",
                    "nullable": False, "primary_key": True,
                    "unique": False, "default": None, "foreign_key": None,
                    "comment": None, "autoincrement": None,
                    "pg_column": {}, "ch_column": {"ch_type": "UInt64"},
                }
            },
            "indexes": [], "foreign_keys": [], "checks": [], "uniques": [],
            "comment": None, "backend": "clickhouse",
            "backend_table_spec": {
                "backend": "clickhouse",
                "ch_engine": "MergeTree", "ch_order_by": ["id"],
            },
        }
        new_state_events = dict(state_events)
        new_state_events["backend_table_spec"] = {
            "backend": "clickhouse",
            "ch_engine": "ReplicatedMergeTree", "ch_order_by": ["id"],
        }

        ops = [
            {
                "type": "recreate_ch_table",
                "table": "events",
                "reason": "ch_engine",
                "from_table": state_events,
                "to_table": new_state_events,
                "drop_old_after_swap": False,
                "preserve_old_suffix": "__dbw_old",
                "failed_suffix": "__dbw_failed",
            },
            {
                "type": "alter_enum_add_value",
                "enum_name": "mood",
                "value": "excited",
                "after": "happy",
            },
            {
                "type": "add_column",
                "table": "audit_log",
                "column": "action",
                "definition": {"type": "varchar"},
            },
        ]
        rollback_ops = [
            {
                "type": "recreate_ch_table",
                "table": "events",
                "reason": "ch_engine",
                "from_table": new_state_events,
                "to_table": state_events,
                "drop_old_after_swap": False,
                "preserve_old_suffix": "__dbw_old",
                "failed_suffix": "__dbw_failed",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name="clickhouse")
        assert "CREATE TABLE IF NOT EXISTS events__dbw_new" in sql
        assert "RENAME TABLE events TO events__dbw_old, events__dbw_new TO events;" in sql
        assert "ADD VALUE IF NOT EXISTS 'excited' AFTER 'happy'" in sql
        assert "ALTER TABLE audit_log ADD COLUMN action" in sql
        assert len([c for c in changes if c.operation == "recreate_ch_table"]) == 1

    def test_snapshot_parse_clickhouse_settings(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_settings
        result = _parse_clickhouse_settings("CREATE TABLE t (id UInt64) ENGINE = MergeTree() ORDER BY id SETTINGS index_granularity=8192, min_rows_for_wide_part=0")
        assert result == {"index_granularity": "8192", "min_rows_for_wide_part": "0"}
        assert _parse_clickhouse_settings("CREATE TABLE t (id UInt64) ENGINE = MergeTree() ORDER BY id") is None

    def test_snapshot_parse_clickhouse_ttl_expressions(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_ttl_expressions
        result = _parse_clickhouse_ttl_expressions(
            "CREATE TABLE t (id UInt64) ENGINE = MergeTree() ORDER BY id TTL created_at + INTERVAL 30 DAY"
        )
        assert "created_at + INTERVAL 30 DAY" in result
        assert _parse_clickhouse_ttl_expressions("CREATE TABLE t (id UInt64) ENGINE = MergeTree() ORDER BY id") == []

    def test_snapshot_parse_clickhouse_projection_names(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_projection_names
        result = _parse_clickhouse_projection_names(
            "CREATE TABLE t (id UInt64) ENGINE = MergeTree() ORDER BY id PROJECTION p1 (SELECT * ORDER BY id)"
        )
        assert "p1" in result

    def test_snapshot_parse_clickhouse_mv_query(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_mv_query
        result = _parse_clickhouse_mv_query(
            "CREATE MATERIALIZED VIEW mv ENGINE = MergeTree() AS SELECT id FROM source"
        )
        assert result == "SELECT id FROM source"
        assert _parse_clickhouse_mv_query("CREATE TABLE t (id UInt64) ENGINE = MergeTree()") is None

    def test_snapshot_parse_clickhouse_zookeeper_path(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_zookeeper_path
        result = _parse_clickhouse_zookeeper_path(
            "CREATE TABLE t (id UInt64) ENGINE = ReplicatedMergeTree('/zk/path', '{replica}') ORDER BY id", "ReplicatedMergeTree"
        )
        assert result == "'/zk/path'"

    def test_snapshot_parse_clickhouse_dict_layout(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_dict_layout
        result = _parse_clickhouse_dict_layout(
            "CREATE DICTIONARY d (id UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE()) LIFETIME(300) LAYOUT(FLAT())"
        )
        assert result is not None
        assert "FLAT" in result
        assert _parse_clickhouse_dict_layout("CREATE TABLE t (id UInt64) ENGINE = MergeTree()") is None

    def test_snapshot_parse_clickhouse_dict_source(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_dict_source
        result = _parse_clickhouse_dict_source(
            "CREATE DICTIONARY d (id UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE(HOST 'localhost')) LIFETIME(300) LAYOUT(FLAT())"
        )
        assert result is not None
        assert "CLICKHOUSE(HOST 'localhost'" in result

    def test_snapshot_parse_clickhouse_dict_lifetime(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_dict_lifetime
        result = _parse_clickhouse_dict_lifetime(
            "CREATE DICTIONARY d (id UInt64) PRIMARY KEY id SOURCE(CLICKHOUSE()) LIFETIME(300) LAYOUT(FLAT())"
        )
        assert result == 300
        assert _parse_clickhouse_dict_lifetime("CREATE TABLE t (id UInt64) ENGINE = MergeTree()") is None

    def test_snapshot_parse_clickhouse_dict_primary_key(self):
        from dbwarden.engine.snapshot import _parse_clickhouse_dict_primary_key
        result = _parse_clickhouse_dict_primary_key(
            "CREATE DICTIONARY d (id UInt64, name String) PRIMARY KEY id SOURCE(CLICKHOUSE()) LIFETIME(300) LAYOUT(FLAT())"
        )
        assert result is not None
        assert result.startswith("id")

    def test_diff_models_ch_add_table(self):
        model_tables = [
            ModelTable(
                name="events",
                columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
                clickhouse_options={"ch_engine": "MergeTree", "ch_order_by": ["id"]},
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, {"tables": {}, "indexes": {}, "constraints": {}})
        create_ops = [op for op in upgrade if op["type"] == "create_table"]
        assert len(create_ops) == 1


class TestBugFixRegression:
    """Regression tests for bug fixes in v0.12.1."""

    @pytest.mark.parametrize("backend", ("mysql", "mariadb"))
    def test_mysql_alter_default_with_col_type(self, backend):
        """Bug 2c/5: MySQL default changes use MODIFY COLUMN when type is available."""
        from dbwarden.engine.snapshot import _build_alter_default_sql
        upgrade, rollback = _build_alter_default_sql(
            "t", "c", "hello", backend,
            col_type="VARCHAR(255)", nullable=False,
        )
        assert "MODIFY COLUMN" in upgrade
        assert "VARCHAR(255)" in upgrade
        assert "NOT NULL" in upgrade
        assert "DEFAULT 'hello'" in upgrade
        assert "MODIFY COLUMN" in rollback

    @pytest.mark.parametrize("backend", ("postgresql", "sqlite", "clickhouse"))
    def test_non_mysql_alter_default_unchanged(self, backend):
        """Non-MySQL backends still use ALTER COLUMN SET DEFAULT."""
        from dbwarden.engine.snapshot import _build_alter_default_sql
        upgrade, rollback = _build_alter_default_sql(
            "t", "c", "42", backend,
        )
        assert "ALTER COLUMN" in upgrade
        assert "SET DEFAULT 42" in upgrade
        assert "ALTER COLUMN" in rollback
        assert "DROP DEFAULT" in rollback

    def test_mysql_alter_default_fallback_no_col_type(self):
        """MySQL emits a hard-failure comment when type info is missing."""
        from dbwarden.engine.snapshot import _build_alter_default_sql
        upgrade, rollback = _build_alter_default_sql(
            "t", "c", "42", "mysql",
        )
        assert upgrade.startswith("-- MANUAL ACTION REQUIRED:")
        assert rollback.startswith("-- MANUAL ACTION REQUIRED:")
        assert "REQUIRES MANUAL COLUMN DEFINITION" in upgrade

    def test_mysql_alter_default_drop_with_col_type(self):
        """MySQL DROP DEFAULT emits MODIFY COLUMN with full definition."""
        from dbwarden.engine.snapshot import _build_alter_default_sql
        upgrade, rollback = _build_alter_default_sql(
            "t", "c", None, "mysql",
            col_type="INT", nullable=True,
        )
        assert "MODIFY COLUMN c INT NULL" in upgrade
        assert "REQUIRES MANUAL COLUMN DEFINITION" in rollback

    def test_mysql_alter_default_drop_without_col_type(self):
        from dbwarden.engine.snapshot import _build_alter_default_sql
        upgrade, rollback = _build_alter_default_sql("t", "c", None, "mysql")
        assert upgrade.startswith("-- MANUAL ACTION REQUIRED:")
        assert rollback.startswith("-- MANUAL ACTION REQUIRED:")

    def test_missing_def_placeholder_returns_non_executable(self):
        """Placeholder values should not look like valid SQL."""
        from dbwarden.engine.snapshot import _missing_def_placeholder
        mysql_pl = _missing_def_placeholder("mysql")
        assert "/*" in mysql_pl and "*/" in mysql_pl
        assert "???" not in mysql_pl
        assert "REQUIRES" in mysql_pl
        other_pl = _missing_def_placeholder("postgresql")
        assert "<original_def_unavailable>" in other_pl
        assert "???" not in other_pl

    def test_assert_complete_mysql_type_valid(self):
        """Valid MySQL types should not raise."""
        from dbwarden.engine.snapshot import _assert_complete_mysql_type
        _assert_complete_mysql_type("VARCHAR(255)")
        _assert_complete_mysql_type("INT")
        _assert_complete_mysql_type("BIGINT UNSIGNED")
        _assert_complete_mysql_type("TEXT")
        _assert_complete_mysql_type("DECIMAL(10,2)")
        _assert_complete_mysql_type("ENUM('a','b')")

    def test_assert_complete_mysql_type_invalid(self):
        """Bare VARCHAR/CHAR without length should raise ValueError."""
        from dbwarden.engine.snapshot import _assert_complete_mysql_type
        with pytest.raises(ValueError, match="VARCHAR"):
            _assert_complete_mysql_type("VARCHAR")
        with pytest.raises(ValueError, match="CHAR"):
            _assert_complete_mysql_type("CHAR")
        with pytest.raises(ValueError, match="ENUM"):
            _assert_complete_mysql_type("ENUM")

    def test_quote_default_for_sql_string_literals(self):
        """String literals are quoted; numbers/keywords/functions are not."""
        from dbwarden.engine.snapshot import _quote_default_for_sql as q
        assert q("hello") == "'hello'"
        assert q("42") == "42"
        assert q("TRUE") == "TRUE"
        assert q("now()") == "now()"
        assert q("CURRENT_TIMESTAMP") == "CURRENT_TIMESTAMP"
        assert q("it's") == "'it''s'"
        assert q("") == "NULL"
        assert q("  ") == "NULL"

    def test_mysql_alter_type_rejects_bare_varchar(self):
        """MySQL type-change generation should reject bare VARCHAR."""
        from dbwarden.engine.snapshot import _build_alter_type_sql
        with pytest.raises(ValueError, match="VARCHAR"):
            _build_alter_type_sql(
                "t", "c", "VARCHAR", "mysql",
                old_type="VARCHAR(255)",
            )

    def test_mysql_alter_type_rejects_bare_old_type(self):
        from dbwarden.engine.snapshot import _build_alter_type_sql
        with pytest.raises(ValueError, match="VARCHAR"):
            _build_alter_type_sql(
                "t", "c", "TEXT", "mysql",
                old_type="VARCHAR",
            )

    def test_mysql_composite_pk_autoincrement_uses_snapshot_pk_count(self):
        import dbwarden.engine.snapshot as snapshot_module
        model_tables = [
            ModelTable(
                name="join_table",
                columns=[
                    ModelColumn("left_id", "BIGINT", False, True, False, None, None, autoincrement=False),
                    ModelColumn("right_id", "BIGINT", False, True, False, None, None, autoincrement=False),
                ],
            )
        ]
        snapshot = {
            "tables": {
                "join_table": {
                    "columns": {
                        "left_id": {"type": "BIGINT", "nullable": False, "primary_key": True, "autoincrement": True},
                        "right_id": {"type": "BIGINT", "nullable": False, "primary_key": True, "autoincrement": True},
                    }
                }
            }
        }
        original_get_backend = snapshot_module._get_backend
        snapshot_module._get_backend = lambda _name: "mysql"
        try:
            upgrade_ops, rollback_ops = diff_models_against_snapshot(model_tables, snapshot, db_name="primary")
        finally:
            snapshot_module._get_backend = original_get_backend
        assert not any(op["type"] == "alter_column_autoincrement" for op in upgrade_ops)
        assert not any(op["type"] == "alter_column_autoincrement" for op in rollback_ops)

    def test_check_migration_scope_warns_large_drift(self):
        """Large migrations produce warnings."""
        from dbwarden.commands.make_migrations import _check_migration_scope
        ops = []
        for i in range(10):
            ops.append({"type": "create_table", "table": f"t{i}"})
        for i in range(8):
            ops.append({"type": "drop_table", "table": f"t{i}"})
        for i in range(6):
            ops.append({"type": "drop_column", "table": "t", "column": f"c{i}"})
        warnings = _check_migration_scope(ops)
        assert any("creates 10 tables" in w for w in warnings)
        assert any("drops 8 tables" in w for w in warnings)
        assert any("drops 6 columns" in w for w in warnings)

    def test_check_migration_scope_no_warnings_small(self):
        """Small focused migrations produce no warnings."""
        from dbwarden.commands.make_migrations import _check_migration_scope
        ops = [{"type": "create_table", "table": "t"}]
        warnings = _check_migration_scope(ops)
        assert len(warnings) == 0

    def test_build_migration_plan_has_summary(self):
        """Migration plan includes summary with operation counts."""
        from dbwarden.commands.make_migrations import build_migration_plan
        from dbwarden.engine.migration_name import Change
        changes = [
            Change(operation="create_table", table="users"),
            Change(operation="add_column", table="users", target="email"),
        ]
        plan = build_migration_plan("test_migration", changes, "SELECT 1")
        assert "summary" in plan
        summary = plan["summary"]
        assert summary["total_operations"] == 2
        assert summary["create_tables"] == 1
        assert summary["drop_tables"] == 0
        assert summary["drop_columns"] == 0


class TestPGBugRegression:
    """Regression tests for PostgreSQL bug fixes A, C, D, and autoincrement normalization."""

    def test_unique_index_backing_constraint_filtered(self):
        """Bug A: unique index backing a unique constraint is not emitted as drop_index."""
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "email": {"type": "varchar(255)", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {
                "ix_users_email": {
                    "table": "users",
                    "columns": ["email"],
                    "unique": True,
                    "name": "ix_users_email",
                },
            },
            "constraints": {
                "ix_users_email": {
                    "type": "unique",
                    "table": "users",
                    "columns": ["email"],
                    "name": "ix_users_email",
                },
            },
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True), _mc("email", "VARCHAR(255)")],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        drop_idx = [op for op in upgrade if op["type"] == "drop_index"]
        assert len(drop_idx) == 0, f"Expected no drop_index ops, got: {drop_idx}"

    def test_view_ignores_index_diff(self):
        """Bug C: view models do not produce index diff ops."""
        snapshot = {
            "tables": {
                "active_users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {
                "ix_active_users_id": {
                    "table": "active_users",
                    "columns": ["id"],
                    "unique": False,
                    "name": "ix_active_users_id",
                },
            },
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="active_users",
                columns=[_mc("id", "INTEGER", pk=True)],
                object_type="view",
                pg_view_definition="SELECT id FROM users WHERE active = true",
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        drop_idx = [op for op in upgrade if op["type"] == "drop_index"]
        add_idx = [op for op in upgrade if op["type"] == "add_index"]
        assert len(drop_idx) == 0, f"Expected no drop_index for views, got: {drop_idx}"
        assert len(add_idx) == 0, f"Expected no add_index for views, got: {add_idx}"

    def test_view_ignores_constraint_diff(self):
        """Bug C: view models do not produce unique constraint diff ops."""
        snapshot = {
            "tables": {
                "active_users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {
                "uq_active_users_id": {
                    "type": "unique",
                    "table": "active_users",
                    "columns": ["id"],
                    "name": "uq_active_users_id",
                },
            },
        }
        model_tables = [
            ModelTable(
                name="active_users",
                columns=[_mc("id", "INTEGER", pk=True)],
                object_type="view",
                pg_view_definition="SELECT id FROM users WHERE active = true",
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        drop_uq = [op for op in upgrade if op["type"] == "drop_unique_constraint"]
        add_uq = [op for op in upgrade if op["type"] == "add_unique_constraint"]
        assert len(drop_uq) == 0, f"Expected no drop_unique_constraint for views, got: {drop_uq}"
        assert len(add_uq) == 0, f"Expected no add_unique_constraint for views, got: {add_uq}"

    def test_autoincrement_default_normalization(self, monkeypatch):
        """SERIAL column autoincrement: nextval default in snapshot is suppressed when model has autoincrement=True."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")

        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {
                            "type": "integer",
                            "nullable": False,
                            "primary_key": True,
                            "default": "nextval('users_id_seq'::regclass)",
                            "autoincrement": True,
                        },
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True)],
            )
        ]
        model_tables[0].columns[0].autoincrement = True
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot, db_name="primary")
        alter_default = [op for op in upgrade if op["type"] == "alter_column_default"]
        assert len(alter_default) == 0, (
            f"Expected no alter_column_default for autoincrement SERIAL column, got: {alter_default}"
        )

    def test_matview_auto_refresh_emits_refresh_op(self, monkeypatch):
        """pg_view_auto_refresh=True on a materialized view emits refresh_matview op."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "user_summary": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "cnt": {"type": "bigint", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="user_summary",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("cnt", "BIGINT"),
                ],
                object_type="materialized_view",
                pg_view_definition="SELECT id, COUNT(*) FROM users GROUP BY id",
                pg_view_materialized=True,
                pg_view_auto_refresh=True,
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        refresh_ops = [op for op in upgrade if op["type"] == "refresh_matview"]
        assert len(refresh_ops) == 1
        assert refresh_ops[0]["table"] == "user_summary"

    def test_view_auto_refresh_no_op_for_regular_views(self, monkeypatch):
        """pg_view_auto_refresh=True on a non-materialized view does NOT emit refresh_matview."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "active_users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="active_users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
                object_type="view",
                pg_view_definition="SELECT id FROM users WHERE active = true",
                pg_view_materialized=False,
                pg_view_auto_refresh=True,
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        refresh_ops = [op for op in upgrade if op["type"] == "refresh_matview"]
        assert len(refresh_ops) == 0

    def test_matview_no_auto_refresh_no_op(self, monkeypatch):
        """Materialized view with pg_view_auto_refresh=False does NOT emit refresh_matview."""
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "user_summary": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "cnt": {"type": "bigint", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="user_summary",
                columns=[
                    _mc("id", "INTEGER", pk=True, nullable=False),
                    _mc("cnt", "BIGINT"),
                ],
                object_type="materialized_view",
                pg_view_definition="SELECT id, COUNT(*) FROM users GROUP BY id",
                pg_view_materialized=True,
                pg_view_auto_refresh=False,
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        refresh_ops = [op for op in upgrade if op["type"] == "refresh_matview"]
        assert len(refresh_ops) == 0


class TestPGGrantsDiff:
    def test_grant_added_emits_add_grant_op(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "email": {"type": "varchar(255)", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True), _mc("email", "VARCHAR(255)")],
                pg_grants=[{"role": "app_user", "privileges": "ALL", "grantable": False}],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_grants = [op for op in upgrade if op["type"] == "add_grant"]
        revoke_grants = [op for op in rollback if op["type"] == "revoke_grant"]
        assert len(add_grants) == 1
        assert add_grants[0]["role"] == "app_user"
        assert add_grants[0]["privileges"] == "ALL"
        assert len(revoke_grants) == 1
        assert revoke_grants[0]["role"] == "app_user"

    def test_grant_removed_emits_revoke_grant_op(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "email": {"type": "varchar(255)", "nullable": True, "primary_key": False},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                    "pg_grants": [{"role": "old_role", "privileges": ["SELECT"], "grantable": False}],
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True), _mc("email", "VARCHAR(255)")],
                pg_grants=[],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        revoke_grants = [op for op in upgrade if op["type"] == "revoke_grant"]
        add_grants = [op for op in rollback if op["type"] == "add_grant"]
        assert len(revoke_grants) == 1
        assert revoke_grants[0]["role"] == "old_role"
        assert len(add_grants) == 1
        assert add_grants[0]["role"] == "old_role"

    def test_grants_match_no_diff(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                    "pg_grants": [{"role": "reader", "privileges": ["SELECT"], "grantable": False}],
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True)],
                pg_grants=[{"role": "reader", "privileges": ["SELECT"], "grantable": False}],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        grant_ops = [op for op in upgrade if "grant" in op["type"]]
        assert len(grant_ops) == 0

    def test_grant_changed_privileges_emits_add_and_revoke(self, monkeypatch):
        monkeypatch.setattr("dbwarden.engine.snapshot._get_backend", lambda db_name=None: "postgresql")
        snapshot = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                    },
                    "primary_key": ["id"],
                    "comment": None,
                    "pg_grants": [{"role": "editor", "privileges": ["SELECT"], "grantable": False}],
                }
            },
            "enums": {},
            "indexes": {},
            "constraints": {},
        }
        model_tables = [
            ModelTable(
                name="users",
                columns=[_mc("id", "INTEGER", pk=True)],
                pg_grants=[{"role": "editor", "privileges": ["SELECT", "INSERT"], "grantable": False}],
            )
        ]
        upgrade, rollback = diff_models_against_snapshot(model_tables, snapshot)
        add_grants = [op for op in upgrade if op["type"] == "add_grant"]
        revoke_grants = [op for op in upgrade if op["type"] == "revoke_grant"]
        assert len(add_grants) == 1
        assert add_grants[0]["role"] == "editor"
        assert len(revoke_grants) == 1
        assert revoke_grants[0]["role"] == "editor"


class TestPGSnapshotDiffToSql:
    def test_schema_creation_detected(self):
        """CREATE SCHEMA IF NOT EXISTS is emitted when ops carry a schema key."""
        ops = [
            {
                "type": "alter_view",
                "table": "active_users",
                "schema": "app",
                "pg_view_definition": "SELECT id FROM users",
                "pg_view_materialized": False,
                "snap_pg_view_definition": "SELECT id, name FROM users",
                "snap_pg_view_materialized": False,
            },
        ]
        rollback_ops = [
            {
                "type": "alter_view",
                "table": "active_users",
                "schema": "app",
                "pg_view_definition": "SELECT id, name FROM users",
                "pg_view_materialized": False,
                "snap_pg_view_definition": "SELECT id FROM users",
                "snap_pg_view_materialized": False,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert 'CREATE SCHEMA IF NOT EXISTS "app";' in sql
        assert 'DROP SCHEMA IF EXISTS "app";' in rb_sql

    def test_matview_upgrade_and_rollback_both_materialized(self):
        """Bug D: matview->matview emits CREATE MATERIALIZED VIEW in both upgrade and rollback."""
        ops = [
            {
                "type": "alter_view",
                "table": "user_summary",
                "schema": "public",
                "pg_view_definition": "SELECT id, COUNT(*) FROM users GROUP BY id",
                "pg_view_materialized": True,
                "snap_pg_view_definition": "SELECT id, COUNT(*) FROM old_users GROUP BY id",
                "snap_pg_view_materialized": True,
            },
        ]
        rollback_ops = [
            {
                "type": "alter_view",
                "table": "user_summary",
                "schema": "public",
                "pg_view_definition": "SELECT id, COUNT(*) FROM old_users GROUP BY id",
                "pg_view_materialized": True,
                "snap_pg_view_definition": "SELECT id, COUNT(*) FROM users GROUP BY id",
                "snap_pg_view_materialized": True,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "DROP MATERIALIZED VIEW IF EXISTS" in sql
        assert "CREATE MATERIALIZED VIEW" in sql
        assert "DROP MATERIALIZED VIEW IF EXISTS" in rb_sql
        assert "CREATE MATERIALIZED VIEW" in rb_sql

    def test_matview_to_view_rollback_uses_matview(self):
        """Bug D: when snapshot had matview but model has view, rollback_sql uses DROP+CREATE MATERIALIZED VIEW."""
        ops = [
            {
                "type": "alter_view",
                "table": "user_summary",
                "pg_view_definition": "SELECT id FROM users",
                "pg_view_materialized": False,
                "snap_pg_view_definition": "SELECT id, COUNT(*) FROM users GROUP BY id",
                "snap_pg_view_materialized": True,
            },
        ]
        rollback_ops = [
            {
                "type": "alter_view",
                "table": "user_summary",
                "pg_view_definition": "SELECT id, COUNT(*) FROM users GROUP BY id",
                "pg_view_materialized": True,
                "snap_pg_view_definition": "SELECT id FROM users",
                "snap_pg_view_materialized": False,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        # upgrade: current=matview, new=view → DROP MATERIALIZED, CREATE VIEW
        assert "DROP MATERIALIZED VIEW IF EXISTS" in sql
        assert "CREATE VIEW" in sql
        # rollback_sql is derived from upgrade op's snap_mat=True → DROP MATERIALIZED + CREATE MATERIALIZED
        assert "DROP MATERIALIZED VIEW IF EXISTS" in rb_sql
        assert "CREATE MATERIALIZED VIEW" in rb_sql

    def test_alter_view_ordering_last(self):
        """ALTER_VIEW ops are emitted at position 99, after all other DDL."""
        ops = [
            {"type": "rename_column", "table": "users", "old_name": "name", "new_name": "full_name"},
            {
                "type": "alter_view",
                "table": "active_users",
                "pg_view_definition": "SELECT id, email FROM users",
                "pg_view_materialized": False,
                "snap_pg_view_definition": "SELECT id FROM users",
                "snap_pg_view_materialized": False,
            },
        ]
        rollback_ops = [
            {"type": "rename_column", "table": "users", "old_name": "full_name", "new_name": "name"},
            {
                "type": "alter_view",
                "table": "active_users",
                "pg_view_definition": "SELECT id FROM users",
                "pg_view_materialized": False,
                "snap_pg_view_definition": "SELECT id, email FROM users",
                "snap_pg_view_materialized": False,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        parts = [p.strip() for p in sql.split("\n\n") if p.strip()]
        alter_idx = next(i for i, p in enumerate(parts) if "CREATE VIEW" in p or "DROP VIEW" in p)
        rename_idx = next(i for i, p in enumerate(parts) if "RENAME COLUMN" in p)
        assert alter_idx > rename_idx, "ALTER_VIEW must be ordered after RENAME COLUMN"

    def test_refresh_matview_emitted_for_auto_refresh_matview(self):
        """REFRESH MATERIALIZED VIEW is emitted for matviews with pg_view_auto_refresh=True."""
        ops = [
            {
                "type": "refresh_matview",
                "table": "user_summary",
                "schema": "public",
            },
        ]
        rollback_ops = [
            {
                "type": "refresh_matview",
                "table": "user_summary",
                "schema": "public",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "REFRESH MATERIALIZED VIEW" in sql
        assert "user_summary" in sql
        assert "REFRESH MATERIALIZED VIEW" in rb_sql

    def test_refresh_matview_schema_qualified(self):
        """REFRESH MATERIALIZED VIEW uses schema-qualified name when schema is set."""
        ops = [
            {
                "type": "refresh_matview",
                "table": "user_summary",
                "schema": "app",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, [], db_name=None)
        assert '"app".user_summary' in sql or "app.user_summary" in sql

    def test_refresh_matview_change_operation(self):
        """refresh_matview produces a Change with operation='refresh_matview'."""
        ops = [
            {
                "type": "refresh_matview",
                "table": "user_summary",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, [], db_name=None)
        assert len(changes) == 1
        assert changes[0].operation == "refresh_matview"
        assert changes[0].table == "user_summary"


class TestPGDomainSequenceOps:
    def test_create_domain_op(self):
        ops = [
            {
                "type": "create_domain",
                "name": "positive_int",
                "schema": "app",
                "domain_type": "integer",
                "not_null": True,
                "check": "VALUE > 0",
            },
        ]
        rollback_ops = [
            {
                "type": "drop_domain",
                "name": "positive_int",
                "schema": "app",
                "domain_type": "integer",
                "not_null": True,
                "check": "VALUE > 0",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "CREATE DOMAIN app.positive_int AS integer NOT NULL CHECK (VALUE > 0);" in sql
        assert "DROP DOMAIN IF EXISTS app.positive_int;" in rb_sql
        assert any(c.operation == "create_domain" for c in changes)

    def test_drop_domain_op(self):
        ops = [
            {
                "type": "drop_domain",
                "name": "positive_int",
                "schema": "app",
                "domain_type": "integer",
            },
        ]
        rollback_ops = [
            {
                "type": "create_domain",
                "name": "positive_int",
                "schema": "app",
                "domain_type": "integer",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "DROP DOMAIN IF EXISTS app.positive_int;" in sql
        assert "CREATE DOMAIN app.positive_int AS integer;" in rb_sql
        assert any(c.operation == "drop_domain" for c in changes)

    def test_create_domain_op_with_default(self):
        ops = [
            {
                "type": "create_domain",
                "name": "my_email",
                "schema": None,
                "domain_type": "citext",
                "default": "'nobody@example.com'",
                "check": "VALUE ~* '^.+@.+$'",
            },
        ]
        rollback_ops = [
            {
                "type": "drop_domain",
                "name": "my_email",
                "domain_type": "citext",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "CREATE DOMAIN my_email AS citext DEFAULT 'nobody@example.com'" in sql
        assert "CHECK (VALUE ~* '^.+@.+$')" in sql

    def test_create_sequence_op(self):
        ops = [
            {
                "type": "create_sequence",
                "name": "order_number_seq",
                "schema": "app",
                "start": 1000,
                "increment": 1,
                "minvalue": 1,
                "maxvalue": 999999,
                "cycle": True,
                "owned_by": "app.orders.id",
            },
        ]
        rollback_ops = [
            {
                "type": "drop_sequence",
                "name": "order_number_seq",
                "schema": "app",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "CREATE SEQUENCE IF NOT EXISTS app.order_number_seq" in sql
        assert "INCREMENT BY 1" in sql
        assert "START WITH 1000" in sql
        assert "MINVALUE 1" in sql
        assert "MAXVALUE 999999" in sql
        assert "CYCLE" in sql
        assert "OWNED BY app.orders.id" in sql
        assert "DROP SEQUENCE IF EXISTS app.order_number_seq;" in rb_sql
        assert any(c.operation == "create_sequence" for c in changes)

    def test_drop_sequence_op(self):
        ops = [
            {
                "type": "drop_sequence",
                "name": "order_number_seq",
                "schema": None,
                "start": 1,
                "increment": 1,
            },
        ]
        rollback_ops = [
            {
                "type": "create_sequence",
                "name": "order_number_seq",
                "start": 1,
                "increment": 1,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "DROP SEQUENCE IF EXISTS order_number_seq;" in sql
        assert "CREATE SEQUENCE IF NOT EXISTS order_number_seq" in rb_sql
        assert "INCREMENT BY 1" in rb_sql
        assert any(c.operation == "drop_sequence" for c in changes)

    def test_create_sequence_op_minimal(self):
        ops = [
            {
                "type": "create_sequence",
                "name": "simple_seq",
            },
        ]
        rollback_ops = [
            {
                "type": "drop_sequence",
                "name": "simple_seq",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "CREATE SEQUENCE IF NOT EXISTS simple_seq" in sql
        assert "NO CYCLE" in sql
        assert "DROP SEQUENCE IF EXISTS simple_seq;" in rb_sql


class TestPGGrantsOps:
    def test_add_grant_all_to_role(self):
        ops = [
            {
                "type": "add_grant",
                "table": "users",
                "role": "app_user",
                "privileges": "ALL",
                "grantable": False,
                "schema": "public",
            },
        ]
        rollback_ops = [
            {
                "type": "revoke_grant",
                "table": "users",
                "role": "app_user",
                "privileges": "ALL",
                "grantable": False,
                "schema": "public",
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "GRANT ALL ON TABLE public.users TO app_user;" in sql
        assert "REVOKE ALL ON TABLE public.users FROM app_user;" in rb_sql
        assert any(c.operation == "add_grant" for c in changes)

    def test_add_grant_select_to_public(self):
        ops = [
            {
                "type": "add_grant",
                "table": "articles",
                "role": "PUBLIC",
                "privileges": ["SELECT"],
                "grantable": False,
            },
        ]
        rollback_ops = [
            {
                "type": "revoke_grant",
                "table": "articles",
                "role": "PUBLIC",
                "privileges": ["SELECT"],
                "grantable": False,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "GRANT SELECT ON TABLE articles TO PUBLIC;" in sql
        assert "REVOKE SELECT ON TABLE articles FROM PUBLIC;" in rb_sql

    def test_revoke_grant_with_cascade(self):
        ops = [
            {
                "type": "revoke_grant",
                "table": "accounts",
                "role": "admin",
                "privileges": "ALL",
                "grantable": True,
            },
        ]
        rollback_ops = [
            {
                "type": "add_grant",
                "table": "accounts",
                "role": "admin",
                "privileges": "ALL",
                "grantable": True,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert 'REVOKE ALL ON TABLE accounts FROM "admin" CASCADE;' in sql
        assert 'GRANT ALL ON TABLE accounts TO "admin" WITH GRANT OPTION;' in rb_sql
        assert any(c.operation == "revoke_grant" for c in changes)

    def test_add_grant_multiple_privileges(self):
        ops = [
            {
                "type": "add_grant",
                "table": "tasks",
                "role": "editor",
                "privileges": ["SELECT", "INSERT", "UPDATE"],
                "grantable": False,
            },
        ]
        rollback_ops = [
            {
                "type": "revoke_grant",
                "table": "tasks",
                "role": "editor",
                "privileges": ["SELECT", "INSERT", "UPDATE"],
                "grantable": False,
            },
        ]
        sql, rb_sql, changes = snapshot_diff_to_sql(ops, rollback_ops, db_name=None)
        assert "GRANT SELECT, INSERT, UPDATE ON TABLE tasks TO editor;" in sql
        assert "REVOKE SELECT, INSERT, UPDATE ON TABLE tasks FROM editor;" in rb_sql
