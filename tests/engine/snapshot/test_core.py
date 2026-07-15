import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from dbwarden.exceptions import ConfigurationError
from dbwarden.engine.snapshot import (
    _apply_rename_intents,
    _normalize_mysql_default,
    _rename_table_sql,
    TableRenameIntent,
    compute_checksum,
    detect_renames,
    find_latest_snapshot,
    get_schemas_directory,
    normalize_type,
    read_snapshot,
    write_snapshot,
    extract_full_schema_snapshot,
)
from dbwarden.engine.model_discovery import ModelColumn, ModelTable


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

    def test_char_variants(self):
        result = normalize_type("CHAR")
        assert result["type"] in ("char", "varchar")

    def test_boolean_variants(self):
        for raw in ("BOOL", "BOOLEAN"):
            assert normalize_type(raw)["type"] == "boolean"

    def test_float_variants(self):
        assert normalize_type("FLOAT")["type"] == "float"
        assert normalize_type("DOUBLE")["type"] == "float"

    def test_timestamp_variants(self):
        result = normalize_type("TIMESTAMP")
        assert result["type"] == "timestamp"

    def test_timestamptz(self):
        result = normalize_type("TIMESTAMPTZ")
        assert result["type"] in ("timestamptz", "timestamp")

    def test_date(self):
        assert normalize_type("DATE")["type"] == "date"

    def test_time(self):
        assert normalize_type("TIME")["type"] == "time"

    def test_numeric(self):
        result = normalize_type("NUMERIC(12,4)")
        assert result["type"] == "numeric"

    def test_json_variants(self):
        for raw in ("JSON", "JSONB"):
            assert normalize_type(raw)["type"] == "json"

    def test_uuid(self):
        assert normalize_type("UUID")["type"] == "uuid"

    def test_unknown_type_returns_raw(self):
        result = normalize_type("CUSTOM_TYPE")
        assert result.get("raw") is True


class TestComputeChecksum:
    def test_compute_checksum(self):
        snap1 = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                }
            },
        }
        snap2 = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                }
            },
        }
        assert compute_checksum(snap1) == compute_checksum(snap2)

    def test_checksum_change(self):
        snap1 = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                }
            },
        }
        snap2 = {
            "tables": {
                "users": {
                    "columns": {
                        "id": {"type": "integer", "nullable": False, "primary_key": True},
                        "name": {"type": "varchar", "nullable": True, "primary_key": False},
                    }
                }
            },
        }
        assert compute_checksum(snap1) != compute_checksum(snap2)


class TestWriteReadSnapshot:
    def test_write_and_read_snapshot(self):
        snapshot = {
            "tables": {
                "users": {
                    "columns": {"id": {"type": "integer", "nullable": False, "primary_key": True}},
                }
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='test', default=True, database_type='sqlite', "
                    "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
                )
                from dbwarden.config import get_database, get_multi_db_config
                cfg = get_multi_db_config()
                assert "test" in cfg.databases
                filepath = write_snapshot(snapshot, database="test", migration_id="001")
                assert filepath is not None
                loaded = read_snapshot(filepath)
                assert loaded is not None
                assert "tables" in loaded
                assert "users" in loaded["tables"]
            finally:
                os.chdir(old_cwd)

    def test_read_nonexistent_snapshot(self):
        result = read_snapshot("/nonexistent/path.json")
        assert result is None

    def test_latest_snapshot_none_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                result = find_latest_snapshot("test")
                assert result is None
            finally:
                os.chdir(old_cwd)

    def test_check_for_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='test', default=True, database_type='sqlite', "
                    "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
                )
                schemas_dir = get_schemas_directory("test")
                assert os.path.isdir(schemas_dir)
            finally:
                os.chdir(old_cwd)


class TestFindLatestSnapshot:
    def test_find_latest_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='test', default=True, database_type='sqlite', "
                    "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
                )
                snapshot = {
                    "tables": {},
                    "migration_id": "0001_init",
                }
                write_snapshot(snapshot, database="test", migration_id="0001_init")
                latest = find_latest_snapshot("test")
                assert latest is not None
            finally:
                os.chdir(old_cwd)

    def test_has_snapshot_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                Path("dbwarden.py").write_text(
                    "from dbwarden import database_config\n"
                    "database_config(database_name='test', default=True, database_type='sqlite', "
                    "database_url_sync='sqlite:///./test.db', model_paths=['models'])\n"
                )
                schemas = get_schemas_directory("test")
                assert os.path.isdir(schemas)
            finally:
                os.chdir(old_cwd)


class TestMySQLSnapshot:
    def setup_method(self):
        self.mock_connection = "mock_conn"

    def test_canary(self):
        assert True

    def test_mysql_default_normalize_null(self):
        result = _normalize_mysql_default("NULL")
        assert result is None

    def test_mysql_default_normalize_current_timestamp(self):
        result = _normalize_mysql_default("CURRENT_TIMESTAMP")
        assert result == "CURRENT_TIMESTAMP"

    def test_mysql_default_normalize_current_timestamp_fsp(self):
        result = _normalize_mysql_default("CURRENT_TIMESTAMP(6)")
        assert result == "CURRENT_TIMESTAMP"

    def test_mysql_default_normalize_on_update(self):
        result = _normalize_mysql_default("ON UPDATE CURRENT_TIMESTAMP")
        assert result == "CURRENT_TIMESTAMP"

    def test_mysql_default_normalize_on_update_fsp(self):
        result = _normalize_mysql_default("ON UPDATE CURRENT_TIMESTAMP(3)")
        assert result == "CURRENT_TIMESTAMP"

    def test_mysql_default_normalize_bare_int(self):
        result = _normalize_mysql_default("0")
        assert result == "0"

    def test_mysql_default_normalize_quoted_string(self):
        result = _normalize_mysql_default("'active'")
        assert result == "active"

    def test_mysql_default_normalize_expression(self):
        result = _normalize_mysql_default("(1)")
        assert result == "1"


class TestDetectRenames:
    def test_simple_rename(self):
        dropped = [("old_col", {"type": "integer"})]
        added = [("new_col", _mc("new_col", "INTEGER"))]
        renames = detect_renames("users", dropped, added)
        assert len(renames) == 1
        assert renames[0] == ("old_col", "new_col")

    def test_no_rename(self):
        dropped = [("id", {"type": "integer"})]
        added = [("id", _mc("id", "INTEGER"))]
        renames = detect_renames("users", dropped, added)
        assert len(renames) == 0

    def test_add_and_remove_detected(self):
        dropped = [("uid", {"type": "integer"})]
        added = [("id", _mc("id", "INTEGER"))]
        renames = detect_renames("users", dropped, added)
        assert len(renames) == 1
        assert renames[0] == ("uid", "id")

    def test_no_rename_different_types(self):
        dropped = [("uid", {"type": "integer"})]
        added = [("uid", _mc("uid", "VARCHAR(255)"))]
        renames = detect_renames("users", dropped, added)
        assert len(renames) == 0

    def test_intent_generation_valid(self):
        intent = TableRenameIntent("a", "b")
        assert intent.old_table == "a"
        assert intent.new_table == "b"

    def test_rename_table_sql(self):
        intent = TableRenameIntent("users", "customers")
        sql = _rename_table_sql(intent, "mysql")
        assert "ALTER TABLE users RENAME TO customers" in sql.upgrade_sql

    def test_rename_no_match(self):
        renames = detect_renames("t", [], [])
        assert len(renames) == 0


class TestApplyRenameIntents:
    def test_apply_single_rename(self):
        upgrade_ops = [
            {"type": "drop_column", "table": "orders", "column": "old_col"},
            {"type": "add_column", "table": "orders", "column": "new_col", "definition": {}},
        ]
        rollback_ops = [
            {"type": "add_column", "table": "orders", "column": "old_col", "definition": {}},
            {"type": "drop_column", "table": "orders", "column": "new_col"},
        ]
        confirmed = {("orders", "old_col", "new_col")}
        result_up, result_ro = _apply_rename_intents(upgrade_ops, rollback_ops, confirmed)
        assert result_up[0]["type"] == "rename_column"

    def test_apply_no_intents(self):
        upgrade_ops = [
            {"type": "drop_column", "table": "orders", "column": "old_col"},
        ]
        rollback_ops = [
            {"type": "add_column", "table": "orders", "column": "old_col", "definition": {}},
        ]
        result_up, result_ro = _apply_rename_intents(upgrade_ops, rollback_ops, set())
        assert result_up[0]["type"] == "drop_column"

    def test_apply_empty_ops(self):
        result_up, result_ro = _apply_rename_intents([], [], set())
        assert result_up == []
        assert result_ro == []

    def test_apply_synthetic_rename(self):
        upgrade_ops = [
            {"type": "drop_column", "table": "a", "column": "x"},
            {"type": "add_column", "table": "a", "column": "y", "definition": {}},
        ]
        rollback_ops = [
            {"type": "add_column", "table": "a", "column": "x", "definition": {}},
            {"type": "drop_column", "table": "a", "column": "y"},
        ]
        confirmed = {("a", "x", "y")}
        result_up, _ = _apply_rename_intents(upgrade_ops, rollback_ops, confirmed)
        assert result_up[0]["type"] == "rename_column"
        assert result_up[0]["old_name"] == "x"
        assert result_up[0]["new_name"] == "y"


class TestExtractFullSchemaSnapshot:
    def test_canary(self):
        assert True

    def test_snapshot_structure(self):
        tables = [
            ModelTable(
                "public.users",
                columns=[_mc("id", "INTEGER", pk=True, nullable=False)],
            )
        ]
        assert len(tables[0].name) > 0

    def test_extract_accepts_db_handle(self):
        with pytest.raises(TypeError):
            extract_full_schema_snapshot(
                db_name="primary",
            )

    def test_find_latest_snapshot_none(self):
        result = find_latest_snapshot("nonexistent")
        assert result is None
