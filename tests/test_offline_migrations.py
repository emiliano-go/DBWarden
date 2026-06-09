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
    assert add_cols[0]["target"] == "email"


def test_diff_drop_column():
    prev = model_state_to_dict([_make_table("users", columns=[
        _make_col("id"), _make_col("email", "varchar"),
    ])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("id")])])
    up, down = diff_model_states(prev, curr)
    drop_cols = [op for op in up if op["type"] == "drop_column"]
    assert len(drop_cols) == 1
    assert drop_cols[0]["target"] == "email"


def test_diff_type_change():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar")])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "text")])])
    up, down = diff_model_states(prev, curr)
    type_changes = [op for op in up if op["type"] == "alter_column_type"]
    assert len(type_changes) == 1
    assert type_changes[0]["target"] == "name"


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


def test_diff_default_change():
    prev = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default=None)])])
    curr = model_state_to_dict([_make_table("users", columns=[_make_col("name", "varchar", default="'default'")])])
    up, down = diff_model_states(prev, curr)
    default_ops = [op for op in up if op["type"] == "alter_column_default"]
    assert len(default_ops) == 1


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


def test_diff_comment_change():
    prev = model_state_to_dict([_make_table("users", comment="Old")])
    curr = model_state_to_dict([_make_table("users", comment="New")])
    up, down = diff_model_states(prev, curr)
    comment_ops = [op for op in up if op["type"] == "alter_comment"]
    assert len(comment_ops) == 1
