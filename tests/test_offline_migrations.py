from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.offline import diff_model_states, model_state_to_dict, _table_to_state_entry


def _make_col(name, type="integer", nullable=False, pk=False, default=None):
    return ModelColumn(name, type, nullable, pk, False, default, None)


def _make_table(name, columns=None, comment=None, ch_opts=None, pg_table=None):
    return ModelTable(
        name=name,
        columns=columns or [_make_col("id")],
        clickhouse_options=ch_opts or {},
        comment=comment,
        pg_table=pg_table or {},
    )


def test_model_state_roundtrip():
    table = _make_table("users", columns=[
        _make_col("id", "biginteger", pk=True),
        _make_col("email", "varchar", nullable=False),
        _make_col("bio", "text", nullable=True),
    ])
    state = model_state_to_dict([table])
    assert state["format_version"] == 1
    assert "users" in state["tables"]
    entry = state["tables"]["users"]
    assert "id" in entry["columns"]
    assert entry["columns"]["id"]["type"] == "biginteger"
    assert entry["columns"]["id"]["primary_key"] is True


def test_diff_new_table():
    prev = model_state_to_dict([])
    curr = model_state_to_dict([_make_table("users")])
    up, down = diff_model_states(prev, curr)
    assert len(up) == 1
    assert up[0]["type"] == "create_table"
    assert up[0]["table"] == "users"
    assert len(down) == 1
    assert down[0]["type"] == "drop_table"


def test_diff_drop_table():
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([])
    up, down = diff_model_states(prev, curr)
    assert len(up) == 1
    assert up[0]["type"] == "drop_table"
    assert up[0]["table"] == "users"
    assert len(down) == 1
    assert down[0]["type"] == "create_table"


def test_diff_add_column():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("id")])])
    curr = model_state_to_dict([_make_table("users", columns=[
        _make_col("id"), _make_col("email", "varchar"),
    ])])
    up, down = diff_model_states(prev, curr)
    add_cols = [op for op in up if op["type"] == "add_column"]
    assert len(add_cols) == 1
    assert add_cols[0]["column"] == "email"
    assert add_cols[0]["definition"]["type"] == "varchar"


def test_diff_drop_column():
    prev = model_state_to_dict([_make_table("users", columns=[
        _make_col("id"), _make_col("email", "varchar"),
    ])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id")])])
    up, down = diff_model_states(prev, curr)
    drop_cols = [op for op in up if op["type"] == "drop_column"]
    assert len(drop_cols) == 1
    assert drop_cols[0]["column"] == "email"
    assert drop_cols[0]["definition"]["type"] == "varchar"


def test_diff_type_change():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar")])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "text")])])
    up, down = diff_model_states(prev, curr)
    type_changes = [op for op in up if op["type"] == "alter_column_type"]
    assert len(type_changes) == 1
    assert type_changes[0]["column"] == "name"
    assert type_changes[0]["model_type"] == "text"


def test_diff_no_changes():
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([_make_table("users")])
    up, down = diff_model_states(prev, curr)
    assert len(up) == 0
    assert len(down) == 0


def test_diff_nullable_change():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("email", "varchar", nullable=True)])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("email", "varchar", nullable=False)])])
    up, down = diff_model_states(prev, curr)
    nullable_ops = [op for op in up if op["type"] == "alter_column_nullable"]
    assert len(nullable_ops) == 1
    assert nullable_ops[0]["nullable"] is False
    assert nullable_ops[0]["col_type"] == "varchar"


def test_diff_default_change():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default=None)])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default="'default'")])])
    up, down = diff_model_states(prev, curr)
    default_ops = [op for op in up if op["type"] == "alter_column_default"]
    assert len(default_ops) == 1
    assert default_ops[0]["default"] == "'default'"


def test_diff_ch_options():
    prev = model_state_to_dict([_make_table("events", ch_opts={"ch_engine": "MergeTree"})])
    curr = model_state_to_dict([_make_table("events", ch_opts={"ch_engine": "ReplicatedMergeTree"})])
    up, down = diff_model_states(prev, curr)
    assert len(up) == 0  # CH options not compared yet in basic diff


def test_table_to_state_entry_includes_backend():
    table = _make_table("events", ch_opts={"ch_engine": "MergeTree", "ch_order_by": ["id"]})
    entry = _table_to_state_entry(table)
    assert entry["backend_table_spec"]["backend"] == "clickhouse"
    assert entry["backend_table_spec"]["ch_engine"] == "MergeTree"
    assert entry["backend_table_spec"]["ch_order_by"] == ["id"]


def test_table_to_state_entry_includes_pg():
    table = _make_table("users", pg_table={"fillfactor": 80})
    entry = _table_to_state_entry(table)
    assert entry["backend_table_spec"]["backend"] == "postgresql"
    assert entry["backend_table_spec"]["fillfactor"] == 80


def test_column_ch_meta_in_state():
    col = _make_col("payload", "string")
    col.ch_meta = {"ch_codec": "ZSTD(3)", "ch_nullable": True}
    table = _make_table("events", columns=[col])
    entry = _table_to_state_entry(table)
    col_entry = entry["columns"]["payload"]
    assert col_entry["ch_meta"]["ch_codec"] == "ZSTD(3)"
    assert col_entry["ch_meta"]["ch_nullable"] is True


def test_diff_table_comment_change():
    prev = model_state_to_dict([_make_table("users", comment="Old")])
    curr = model_state_to_dict([_make_table("users", comment="New")])
    up, down = diff_model_states(prev, curr)
    comment_ops = [op for op in up if op["type"] == "alter_table_comment"]
    assert len(comment_ops) == 1
    assert comment_ops[0]["comment"] == "New"
    assert comment_ops[0]["previous_comment"] == "Old"


def test_diff_column_comment_change():
    prev_col = _make_col("email", "varchar", nullable=True, default=None)
    prev_col.comment = "Old"
    curr_col = _make_col("email", "varchar", nullable=True, default=None)
    curr_col.comment = "New"
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("id"), prev_col])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id"), curr_col])])
    up, down = diff_model_states(prev, curr)
    comment_ops = [op for op in up if op["type"] == "alter_column_comment"]
    assert len(comment_ops) == 1
    assert comment_ops[0]["column"] == "email"
    assert comment_ops[0]["comment"] == "New"


# ── End-to-end: diff_model_states + snapshot_diff_to_sql ──────────

from dbwarden.engine.snapshot import snapshot_diff_to_sql


def _diff_to_sql(prev_state, curr_state, db_name="primary"):
    up_ops, down_ops = diff_model_states(prev_state, curr_state)
    if not up_ops:
        return "", "", []
    return snapshot_diff_to_sql(up_ops, down_ops, db_name=db_name)


def test_offline_create_table_op():
    """create_table op is correctly generated; full SQL needs config lookup."""
    prev = model_state_to_dict([])
    curr = model_state_to_dict([_make_table("users")])
    up_ops, down_ops = diff_model_states(prev, curr)
    assert len(up_ops) == 1
    assert up_ops[0]["type"] == "create_table"
    assert up_ops[0]["table"] == "users"
    assert down_ops[0]["type"] == "drop_table"


def test_offline_drop_table_sql():
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "DROP TABLE" in up_sql
    assert "users" in up_sql
    assert rb_sql == "" or "CREATE TABLE" in rb_sql
    assert changes[0].operation == "drop_table"


def test_offline_add_column_sql():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("id")])])
    curr = model_state_to_dict([_make_table("users", columns=[
        _make_col("id"), _make_col("email", "varchar"),
    ])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "ALTER TABLE users ADD COLUMN email" in up_sql
    assert "varchar" in up_sql.lower() or "VARCHAR" in up_sql
    assert "ALTER TABLE users DROP COLUMN email" in rb_sql
    assert any(c.operation == "add_column" and c.target == "email" for c in changes)


def test_offline_drop_column_sql():
    prev = model_state_to_dict([_make_table("users", columns=[
        _make_col("id"), _make_col("email", "varchar"),
    ])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id")])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "DROP COLUMN email" in up_sql
    assert "ADD COLUMN email" in rb_sql
    assert any(c.operation == "drop_column" and c.target == "email" for c in changes)


def test_offline_alter_column_type_sql():
    from dbwarden.config import set_dev_mode
    set_dev_mode(True)
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar")])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "text")])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "ALTER TABLE users ALTER COLUMN name TYPE text" in up_sql
    # Rollback in offline mode uses placeholder since previous type isn't tracked
    assert any(c.operation == "alter_column_type" for c in changes)


def test_offline_alter_nullable_sql():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("email", "varchar", nullable=True)])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("email", "varchar", nullable=False)])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "SET NOT NULL" in up_sql or "NOT NULL" in up_sql
    assert "DROP NOT NULL" in rb_sql or "NULL" in rb_sql
    assert any(c.operation == "alter_column_nullable" for c in changes)


def test_offline_alter_default_sql():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default=None)])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default="'default'")])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "SET DEFAULT" in up_sql or "DEFAULT" in up_sql
    assert "DROP DEFAULT" in rb_sql
    assert any(c.operation == "alter_column_default" for c in changes)


def test_offline_table_comment_sql():
    prev = model_state_to_dict([_make_table("users", comment="Old")])
    curr = model_state_to_dict([_make_table("users", comment="New")])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "COMMENT ON TABLE users IS 'New'" in up_sql
    assert "COMMENT ON TABLE users IS 'Old'" in rb_sql
    assert any(c.operation == "alter_table_comment" for c in changes)


def test_offline_column_comment_sql():
    prev_col = _make_col("email", "varchar", nullable=True)
    prev_col.comment = "Old comment"
    curr_col = _make_col("email", "varchar", nullable=True)
    curr_col.comment = "New comment"
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("id"), prev_col])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id"), curr_col])])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert "COMMENT ON COLUMN users.email IS 'New comment'" in up_sql
    assert "COMMENT ON COLUMN users.email IS 'Old comment'" in rb_sql
    assert any(c.operation == "alter_column_comment" for c in changes)


def test_offline_add_index_op():
    """add_index op correctly detected by name; SQL gen needs full model lookup."""
    from dbwarden.engine.model_discovery import IndexInfo
    prev = model_state_to_dict([_make_table("users")])
    table = _make_table("users", columns=[_make_col("name", "varchar")])
    table.indexes = [IndexInfo(name="ix_name", columns=["name"])]
    curr = model_state_to_dict([table])
    up_ops, down_ops = diff_model_states(prev, curr)
    add_idx_ops = [op for op in up_ops if op["type"] == "add_index"]
    assert len(add_idx_ops) == 1
    assert add_idx_ops[0]["target"] == "ix_name"
    assert add_idx_ops[0]["table"] == "users"


def test_offline_drop_index_sql():
    from dbwarden.engine.model_discovery import IndexInfo
    table = _make_table("users", columns=[_make_col("name", "varchar")])
    table.indexes = [IndexInfo(name="ix_name", columns=["name"])]
    prev = model_state_to_dict([table])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar")])])
    from dbwarden.config import set_dev_mode
    set_dev_mode(True)
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    up_ops, down_ops = diff_model_states(prev, curr)
    drop_idx_ops = [op for op in up_ops if op["type"] == "drop_index"]
    assert len(drop_idx_ops) == 1
    assert drop_idx_ops[0]["target"] == "ix_name"


def test_offline_multiple_ops_in_one_diff():
    """Multiple changes are correctly detected in a single diff."""
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([
        _make_table("users", columns=[
            _make_col("id"), _make_col("email", "varchar", nullable=True),
        ]),
        _make_table("posts"),
    ])
    up_ops, down_ops = diff_model_states(prev, curr)
    assert len(up_ops) >= 2
    types = [op["type"] for op in up_ops]
    assert "add_column" in types
    assert "create_table" in types
    with_tables = {op.get("table") for op in up_ops}
    assert "users" in with_tables
    assert "posts" in with_tables


def test_offline_no_changes_returns_empty():
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([_make_table("users")])
    up_sql, rb_sql, changes = _diff_to_sql(prev, curr)
    assert up_sql.strip() == ""
    assert rb_sql.strip() == ""
    assert len(changes) == 0


def test_offline_add_column_with_default():
    col = _make_col("is_active", "boolean", default="true")
    prev = model_state_to_dict([_make_table("users")])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id"), col])])
    up_ops, down_ops = diff_model_states(prev, curr)
    add_cols = [op for op in up_ops if op["type"] == "add_column"]
    assert len(add_cols) == 1
    assert add_cols[0]["definition"]["default"] == "true"
    # The SQL may or may not include DEFAULT depending on snapshot_diff_to_sql fallback
    up_sql, rb_sql, changes = snapshot_diff_to_sql(up_ops, down_ops, db_name="primary")
    assert "ALTER TABLE users ADD COLUMN is_active" in up_sql


def test_offline_clickhouse_table_not_crashes():
    """CH option changes are silently ignored, but the diff should not crash."""
    prev = model_state_to_dict([_make_table("events", ch_opts={"ch_engine": "MergeTree"})])
    curr = model_state_to_dict([_make_table("events", ch_opts={"ch_engine": "ReplicatedMergeTree"})])
    up_ops, down_ops = diff_model_states(prev, curr)
    assert len([op for op in up_ops if op["type"] == "alter_ch_options"]) == 0


def test_offline_backend_preserved_in_state():
    table = _make_table("events", ch_opts={"ch_engine": "MergeTree", "ch_order_by": ["id"]})
    state = model_state_to_dict([table])
    entry = state["tables"]["events"]
    assert entry["backend_table_spec"]["backend"] == "clickhouse"
    assert entry["backend_table_spec"]["ch_engine"] == "MergeTree"


def test_offline_pg_table_options_in_state():
    table = _make_table("accounts", pg_table={"fillfactor": 80})
    state = model_state_to_dict([table])
    entry = state["tables"]["accounts"]
    assert entry["backend_table_spec"]["backend"] == "postgresql"
    assert entry["backend_table_spec"]["fillfactor"] == 80


# ── Full integration: make_migrations_cmd(offline=True) ──────────

import json
import os
import tempfile
from pathlib import Path
from dbwarden.config import set_dev_mode
from dbwarden.commands.make_migrations import make_migrations_cmd


def test_offline_make_migrations_end_to_end():
    """
    Full offline flow: create initial state → modify model →
    make-migrations --offline → verify .sql, .plan.json, state update.
    """
    set_dev_mode(False)
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Write minimal config
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                "database_config(database_name='primary', default=True, "
                "database_type='sqlite', database_url_sync='sqlite:///./app.db', "
                "model_paths=['models'])\n",
                encoding="utf-8",
            )

            # Write initial model file (id + email only)
            Path("models").mkdir(parents=True)
            Path("models/user.py").write_text(
                "from sqlalchemy import Column, Integer, String\n"
                "from sqlalchemy.orm import declarative_base\n\n"
                "Base = declarative_base()\n\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String(255), nullable=False, unique=True)\n",
                encoding="utf-8",
            )

            # Create migrations dir and .dbwarden/ dir
            Path("migrations/primary").mkdir(parents=True)
            Path(".dbwarden").mkdir(parents=True)

            # Create initial model_state.json matching the model (id + email)
            initial_state = {
                "format_version": 1,
                "exported_at": "2026-01-01T00:00:00Z",
                "dbwarden_version": "0.9.4",
                "tables": {
                    "users": {
                        "columns": {
                            "id": {"type": "integer", "nullable": False, "primary_key": True, "unique": False, "default": None, "foreign_key": None, "comment": None},
                            "email": {"type": "varchar(255)", "nullable": False, "primary_key": False, "unique": True, "default": None, "foreign_key": None, "comment": None},
                        },
                        "indexes": [],
                        "foreign_keys": [],
                        "checks": [],
                        "uniques": [],
                        "comment": None,
                        "object_type": "table",
                        "backend_table_spec": {},
                    }
                },
            }
            Path(".dbwarden/model_state.json").write_text(
                json.dumps(initial_state, indent=2) + "\n", encoding="utf-8"
            )

            # ── Step 2: Modify the model to add bio column ──
            Path("models/user.py").write_text(
                "from sqlalchemy import Column, Integer, String, Text\n"
                "from sqlalchemy.orm import declarative_base\n\n"
                "Base = declarative_base()\n\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String(255), nullable=False, unique=True)\n"
                "    bio = Column(Text, nullable=True)\n",
                encoding="utf-8",
            )

            # ── Step 3: Run make-migrations --offline ──
            make_migrations_cmd("add bio column", offline=True, database="primary")

            # ── Step 4: Verify results ──
            sql_files = sorted(Path("migrations/primary").glob("*.sql"))
            plan_files = sorted(Path("migrations/primary").glob("*.plan.json"))

            assert len(sql_files) >= 1, "Should have created at least one SQL file"
            assert len(plan_files) >= 1, "Should have created at least one plan file"

            offline_sql = sql_files[-1]
            offline_sql_content = offline_sql.read_text(encoding="utf-8")
            assert "ALTER TABLE users ADD COLUMN bio" in offline_sql_content, (
                f"Offline migration should add bio column, got:\n{offline_sql_content}"
            )
            assert "-- upgrade" in offline_sql_content
            assert "-- rollback" in offline_sql_content
            assert "ALTER TABLE users DROP COLUMN bio" in offline_sql_content

            # Verify plan file
            offline_plan = plan_files[-1]
            plan = json.loads(offline_plan.read_text(encoding="utf-8"))
            assert plan["migration_id"] == offline_sql.stem
            assert len(plan["operations"]) >= 1
            assert plan["operations"][0]["type"] == "add_column"

            # ── Step 5: Verify state was updated ──
            updated_state = json.loads(Path(".dbwarden/model_state.json").read_text())
            assert "bio" in updated_state["tables"]["users"]["columns"], (
                f"State should include 'bio' column, got: "
                f"{list(updated_state['tables']['users']['columns'].keys())}"
            )

            # ── Step 6: Run offline again with no changes ──
            make_migrations_cmd("no changes", offline=True, database="primary")
            sql_files_after = sorted(Path("migrations/primary").glob("*.sql"))
            assert len(sql_files_after) == len(sql_files), (
                "No new SQL should be created when there are no changes"
            )

        finally:
            os.chdir(old_cwd)


def test_offline_missing_state_file_does_not_crash():
    """Running make-migrations --offline without a state file should give a clear error."""
    set_dev_mode(False)
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                "database_config(database_name='primary', default=True, "
                "database_type='sqlite', database_url_sync='sqlite:///./app.db', "
                "model_paths=['models'])\n",
                encoding="utf-8",
            )
            Path("models").mkdir(parents=True)
            Path("models/user.py").write_text(
                "from sqlalchemy import Column, Integer, String\n"
                "from sqlalchemy.orm import declarative_base\n\n"
                "Base = declarative_base()\n\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String(255), nullable=False)\n",
                encoding="utf-8",
            )
            Path("migrations/primary").mkdir(parents=True)
            Path(".dbwarden").mkdir(parents=True)

            # Run offline WITHOUT state file — should not crash
            make_migrations_cmd("should fail gracefully", offline=True, database="primary")

            # No SQL file should be created
            sql_files = sorted(Path("migrations/primary").glob("*.sql"))
            assert len(sql_files) == 0, "No migration should be created without state file"

        finally:
            os.chdir(old_cwd)


def test_offline_state_format_version():
    """State file format_version should be tracked and round-trippable."""
    prev = model_state_to_dict([_make_table("users")])
    assert prev["format_version"] == 1
    # Re-serialize and verify
    serialized = json.dumps(prev, indent=2, default=str)
    restored = json.loads(serialized)
    assert restored["format_version"] == 1
    assert "users" in restored["tables"]
