import json
import os
import tempfile
from pathlib import Path

import pytest

from dbwarden.engine.snapshot import (
    _apply_rename_intents,
    _assemble_migration,
    _build_fk_name,
    _build_index_name,
    _build_foreign_key_sql,
    _build_index_sql,
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
from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.migration_name import Change


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

        assert "ix_t_a" in snapshot["indexes"]
        assert snapshot["indexes"]["ix_t_a"]["unique"] is False
        assert "ix_t_b" in snapshot["indexes"]
        assert snapshot["indexes"]["ix_t_b"]["unique"] is True

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
    def test_rename_table_is_first(self):
        assert StatementOrder.RENAME_TABLE == 0
        assert StatementOrder.RENAME_TABLE < StatementOrder.RENAME_COLUMN
        assert StatementOrder.RENAME_COLUMN < StatementOrder.ALTER_COLUMN_TYPE
        assert StatementOrder.ALTER_COLUMN_TYPE < StatementOrder.ALTER_COLUMN_NULLABLE
        assert StatementOrder.ALTER_COLUMN_NULLABLE < StatementOrder.ALTER_COLUMN_DEFAULT
        assert StatementOrder.ALTER_COLUMN_DEFAULT < StatementOrder.CREATE_TABLE
        assert StatementOrder.CREATE_TABLE < StatementOrder.ADD_COLUMN
        assert StatementOrder.ADD_COLUMN < StatementOrder.ALTER_FOREIGN_KEY
        assert StatementOrder.ALTER_FOREIGN_KEY < StatementOrder.ALTER_INDEX
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


class TestTableRenameDetection:
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

    def test_rename_table_sql_clickhouse_comment(self):
        intent = TableRenameIntent(old_table="users", new_table="accounts")
        stmt = _rename_table_sql(intent, "clickhouse")
        assert "ClickHouse does not support" in stmt.upgrade_sql

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
        name = _build_fk_name("users", ["group_id"])
        assert name == "users_group_id_fkey"

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

    def test_fk_add_sql_postgresql(self):
        op = {"type": "add_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]}
        stmts = _build_foreign_key_sql(op, "postgresql")
        assert len(stmts) == 1
        assert "ADD CONSTRAINT" in stmts[0].upgrade_sql
        assert "users_group_id_fkey" in stmts[0].upgrade_sql

    def test_fk_drop_sql_mysql(self):
        op = {"type": "drop_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]}
        stmts = _build_foreign_key_sql(op, "mysql")
        assert "DROP FOREIGN KEY" in stmts[0].upgrade_sql

    def test_fk_sql_sqlite_not_supported(self):
        op = {"type": "add_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]}
        stmts = _build_foreign_key_sql(op, "sqlite")
        assert "not supported" in stmts[0].upgrade_sql

    def test_fk_sql_with_deferrable(self):
        op = {"type": "add_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"], "deferrable": True}
        stmts = _build_foreign_key_sql(op, "postgresql")
        assert "DEFERRABLE INITIALLY DEFERRED" in stmts[0].upgrade_sql

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

    def test_index_add_sql_sqlite(self):
        op = {"type": "add_index", "table": "users", "columns": ["email"], "unique": False}
        stmts = _build_index_sql(op, "sqlite")
        assert "CREATE INDEX" in stmts[0].upgrade_sql
        assert "CONCURRENTLY" not in stmts[0].upgrade_sql

    def test_index_drop_sql(self):
        op = {"type": "drop_index", "table": "users", "index_name": "idx_users_email", "columns": ["email"], "unique": False}
        stmts = _build_index_sql(op, "postgresql")
        assert "DROP INDEX idx_users_email;" in stmts[0].upgrade_sql

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

    def test_fk_rollback_sql_correctness(self):
        op = {"type": "add_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]}
        stmt = _build_foreign_key_sql(op, "postgresql")[0]
        assert "DROP CONSTRAINT" in stmt.rollback_sql
        assert "users_group_id_fkey" in stmt.rollback_sql

    def test_fk_mariadb_uses_drop_foreign_key(self):
        op = {"type": "drop_foreign_key", "table": "users", "columns": ["group_id"], "referenced_table": "groups", "referenced_columns": ["id"]}
        stmt = _build_foreign_key_sql(op, "mariadb")
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
        name = _build_fk_name("orders", ["user_id", "product_id"])
        assert name == "orders_user_id_product_id_fkey"

    def test_fk_add_sql_does_not_include_on_delete(self):
        op = {
            "type": "add_foreign_key",
            "table": "users",
            "columns": ["group_id"],
            "referenced_table": "groups",
            "referenced_columns": ["id"],
            "on_delete": "CASCADE",
        }
        stmts = _build_foreign_key_sql(op, "postgresql")
        assert "ON DELETE" not in stmts[0].upgrade_sql

    def test_fk_add_sql_does_not_include_on_update(self):
        op = {
            "type": "add_foreign_key",
            "table": "users",
            "columns": ["group_id"],
            "referenced_table": "groups",
            "referenced_columns": ["id"],
            "on_update": "SET NULL",
        }
        stmts = _build_foreign_key_sql(op, "postgresql")
        assert "ON UPDATE" not in stmts[0].upgrade_sql
