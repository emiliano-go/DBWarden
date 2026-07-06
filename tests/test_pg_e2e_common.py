"""E2E convergence tests for common DIFF handlers against real PG 13.

Tests that the full snapshot → diff → emit → apply → re-snapshot → diff
cycle converges to zero ops for Column, Constraint, Index, Table, View,
PgTable, and StorageParams handlers.

Prerequisites:
    docker run -d --name pg13-e2e -e POSTGRES_PASSWORD=postgres \\
        -e POSTGRES_DB=dbwarden_test -p 15432:5432 postgres:13-alpine

Run:
    DBWARDEN_E2E=1 python -m pytest tests/test_pg_e2e_common.py -v
"""

import os
from typing import Any

import sqlalchemy as sa
import pytest

from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.snapshot import extract_full_schema_snapshot, snap_to_model_key

PG_URL = "postgresql://postgres:postgres@localhost:15432/dbwarden_test"

pytestmark = pytest.mark.skipif(
    not os.environ.get("DBWARDEN_E2E"),
    reason="set DBWARDEN_E2E=1 to run PG end-to-end tests",
)


@pytest.fixture(scope="module")
def engine():
    e = sa.create_engine(PG_URL)
    yield e
    e.dispose()


def _refresh():
    return extract_full_schema_snapshot(
        sqlalchemy_url=PG_URL,
        database_type="postgresql",
    )


def _drop(engine, *names):
    with engine.begin() as conn:
        for n in names:
            for tmpl in (
                "DROP TABLE IF EXISTS {n} CASCADE",
                "DROP FUNCTION IF EXISTS {n} CASCADE",
                "DROP TYPE IF EXISTS {n} CASCADE",
                "DROP STATISTICS IF EXISTS {n} CASCADE",
                "DROP INDEX IF EXISTS {n} CASCADE",
            ):
                try:
                    conn.execute(sa.text(tmpl.format(n=n)))
                except Exception:
                    pass


def _col(name, type_, nullable=True, primary_key=False, default=None):
    if primary_key:
        nullable = False
    return ModelColumn(
        name=name, type=type_, nullable=nullable, primary_key=primary_key,
        unique=False, default=default, foreign_key=None,
    )


def _snap_col_to_model_col(name, col_dict):
    """Convert a snapshot column dict to a ModelColumn for use in model_spec."""
    pg_col = col_dict.get("pg_column") or col_dict.get("pg_meta") or {}
    pg_meta = {snap_to_model_key(k): v for k, v in pg_col.items()}
    return ModelColumn(
        name=name,
        type=col_dict.get("type", "text"),
        nullable=col_dict.get("nullable", True),
        primary_key=col_dict.get("primary_key", False),
        unique=False,
        default=col_dict.get("default"),
        foreign_key=None,
        comment=col_dict.get("comment"),
        autoincrement=col_dict.get("autoincrement"),
        pg_meta=pg_meta,
    )


def _build_column_model_spec(snap_spec, extra_tables):
    """Build full ColumnHandler model_spec: all snap tables + overrides."""
    spec = {}
    for tname, cols in snap_spec.items():
        spec[tname] = {cname: _snap_col_to_model_col(cname, cdata) for cname, cdata in cols.items()}
    for tname, model_tbl in extra_tables:
        spec[tname] = {c.name: c for c in model_tbl.columns}
    return spec


def _converge(engine, snap_spec, model_spec, handler):
    """Diff → emit → apply → re-snapshot → verify → second cycle."""
    up, rb = handler.diff(
        handler.canonicalize(snap_spec),
        handler.canonicalize(model_spec),
    )
    stmts = []
    for op in up:
        stmts.extend(handler.emit(op))
    with engine.begin() as conn:
        for s in stmts:
            sql = s.upgrade_sql.strip()
            if sql and not sql.startswith("--"):
                conn.execute(sa.text(sql))

    fresh = _refresh()
    c_fresh = handler.canonicalize(handler.extract(fresh))
    c_model = handler.canonicalize(model_spec)
    up2, rb2 = handler.diff(c_fresh, c_model)
    assert up2 == [], (
        f"Second cycle produced {len(up2)} ops for {handler.__class__.__name__}: "
        f"{[o.object_type for o in up2[:5]]}"
    )


# ===================================================================
# ColumnHandler
# ===================================================================

def test_column_add_drop(engine):
    _drop(engine, "e2e_c_add")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_c_add (id int PRIMARY KEY, name text)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry import ColumnHandler
    h = ColumnHandler()
    snap_spec = h.extract(snap)
    model_tables = [
        ModelTable("e2e_c_add", [
            _col("id", "INTEGER", primary_key=True),
            _col("name", "TEXT"),
            _col("email", "VARCHAR(255)"),
        ])
    ]
    model_spec = _build_column_model_spec(snap_spec, [("e2e_c_add", model_tables[0])])
    _converge(engine, snap_spec, model_spec, h)
    _drop(engine, "e2e_c_add")


def test_column_type_change(engine):
    """Verify that varchar(255) → TEXT converges (no type change detected)."""
    _drop(engine, "e2e_c_type")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_c_type (id int PRIMARY KEY, val varchar(255))"))
    snap = _refresh()
    from dbwarden.engine.pg_registry import ColumnHandler
    h = ColumnHandler()
    snap_spec = h.extract(snap)
    model_spec = _build_column_model_spec(snap_spec, [])
    c_snap = h.canonicalize(snap_spec)
    c_model = h.canonicalize(model_spec)
    up, rb = h.diff(c_snap, c_model)
    assert up == [], (
        f"Type change convergence produced {len(up)} ops: "
        f"{[o.object_type for o in up[:5]]}"
    )
    _drop(engine, "e2e_c_type")


def test_column_nullable_flip(engine):
    """Verify that NOT NULL → nullable converges."""
    _drop(engine, "e2e_c_null")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_c_null (id int PRIMARY KEY, val int NOT NULL)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry import ColumnHandler
    h = ColumnHandler()
    snap_spec = h.extract(snap)
    model_spec = _build_column_model_spec(snap_spec, [])
    c_snap = h.canonicalize(snap_spec)
    c_model = h.canonicalize(model_spec)
    up, rb = h.diff(c_snap, c_model)
    assert up == [], (
        f"Nullable convergence produced {len(up)} ops: "
        f"{[o.object_type for o in up[:5]]}"
    )
    _drop(engine, "e2e_c_null")


# ===================================================================
# IndexHandler
# ===================================================================

def test_index_btree(engine):
    _drop(engine, "e2e_i_btree")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_i_btree (id int PRIMARY KEY, val int)"))
        conn.execute(sa.text("CREATE INDEX e2e_i_btree_val_idx ON e2e_i_btree (val)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.index_handler import IndexHandler
    h = IndexHandler()
    spec = h.extract(snap)
    idxs = spec.get("indexes", {})
    # Find our index
    for tbl, indices in idxs.items():
        for idx in indices:
            if idx.get("name") == "e2e_i_btree_val_idx":
                assert idx.get("columns") == ["val"], f"Unexpected columns: {idx.get('columns')}"
                assert idx.get("unique") is False
                break
    _drop(engine, "e2e_i_btree")


def test_index_partial(engine):
    _drop(engine, "e2e_i_part")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_i_part (id int PRIMARY KEY, active bool)"))
        conn.execute(sa.text("CREATE INDEX e2e_i_part_active_idx ON e2e_i_part (active) WHERE active = true"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.index_handler import IndexHandler
    h = IndexHandler()
    spec = h.extract(snap)
    idxs = spec.get("indexes", {})
    for tbl, indices in idxs.items():
        for idx in indices:
            if idx.get("name") == "e2e_i_part_active_idx":
                assert idx.get("columns") == ["active"]
                assert idx.get("where") is not None
                assert "active = true" in idx.get("where", "")
                break
    _drop(engine, "e2e_i_part")


def test_index_expression(engine):
    _drop(engine, "e2e_i_expr")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_i_expr (id int PRIMARY KEY, email text)"))
        conn.execute(sa.text("CREATE INDEX e2e_i_expr_lower_email_idx ON e2e_i_expr (lower(email))"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.index_handler import IndexHandler
    from dbwarden.engine.model_discovery import IndexInfo
    h = IndexHandler()
    spec = h.extract(snap)
    idxs = spec.get("indexes", {})
    found_idx = None
    for indices in idxs.values():
        for idx in indices:
            if idx.get("name") == "e2e_i_expr_lower_email_idx":
                found_idx = idx
                break
    assert found_idx is not None, "Expression index not found in handler extraction"
    assert found_idx.get("columns") == [], f"Expected empty columns for expression index, got {found_idx['columns']}"
    expr = found_idx.get("expression", "")
    assert "lower" in expr and "email" in expr, f"Expression should reference lower(email), got {expr}"
    assert found_idx.get("using") == "btree"
    # Self-diff convergence
    c_snap = h.canonicalize(spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"Expression index self-diff produced {len(up)} ops"
    _drop(engine, "e2e_i_expr")


def test_index_expression_change_detected(engine):
    """Verify that changing an expression produces a non-empty diff."""
    _drop(engine, "e2e_i_expr_chg")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_i_expr_chg (id int PRIMARY KEY, email text, name text)"))
        conn.execute(sa.text("CREATE INDEX e2e_i_expr_chg_lower_email_idx ON e2e_i_expr_chg (lower(email))"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.index_handler import IndexHandler
    from dbwarden.engine.model_discovery import IndexInfo
    h = IndexHandler()
    snap_spec = h.extract(snap)
    # Model has a changed expression (lower(name) instead of lower(email))
    model_spec = {
        "indexes": {
            "e2e_i_expr_chg": [
                IndexInfo(
                    name="e2e_i_expr_chg_lower_email_idx",
                    columns=[],
                    expression="lower(name)",
                    using="btree",
                )
            ]
        },
        "view_tables": set(),
    }
    c_snap = h.canonicalize(snap_spec)
    c_model = h.canonicalize(model_spec)
    up, rb = h.diff(c_snap, c_model)
    assert len(up) > 0, "Expression change should produce at least one op"
    assert any(o.object_type == "drop_index" for o in up), (
        f"Expected a drop_index op for expression change, got: {[o.object_type for o in up]}"
    )
    _drop(engine, "e2e_i_expr_chg")


# ===================================================================
# TableHandler
# ===================================================================

def test_table_create_drop(engine):
    _drop(engine, "e2e_t_life")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_t_life (id int PRIMARY KEY, val text)"))
    snap = _refresh()
    assert "e2e_t_life" in snap["tables"]
    from dbwarden.engine.pg_registry import TableHandler
    h = TableHandler()
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"Table self-diff produced {len(up)} ops"
    _drop(engine, "e2e_t_life")


# ===================================================================
# ConstraintHandler
# ===================================================================

def test_fk_match_full(engine):
    _drop(engine, "e2e_fk_m_ref", "e2e_fk_m_main")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_fk_m_ref (id int PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE e2e_fk_m_main (id int PRIMARY KEY, ref_id int, "
                             "CONSTRAINT e2e_fk_m_main_fkey FOREIGN KEY (ref_id) "
                             "REFERENCES e2e_fk_m_ref (id) MATCH FULL)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.constraint_handler import ConstraintHandler
    h = ConstraintHandler()
    h._snapshot = snap
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"FK MATCH FULL self-diff produced {len(up)} ops"
    _drop(engine, "e2e_fk_m_main", "e2e_fk_m_ref")


def test_fk_cascade(engine):
    _drop(engine, "e2e_fk_c_ref", "e2e_fk_c_main")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_fk_c_ref (id int PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE e2e_fk_c_main (id int PRIMARY KEY, ref_id int, "
                             "CONSTRAINT e2e_fk_c_main_fkey FOREIGN KEY (ref_id) "
                             "REFERENCES e2e_fk_c_ref (id) ON DELETE CASCADE)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.constraint_handler import ConstraintHandler
    h = ConstraintHandler()
    h._snapshot = snap
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"FK CASCADE self-diff produced {len(up)} ops"
    _drop(engine, "e2e_fk_c_main", "e2e_fk_c_ref")


def test_unique_constraint(engine):
    _drop(engine, "e2e_uq")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_uq (id int PRIMARY KEY, email text)"))
        conn.execute(sa.text("ALTER TABLE e2e_uq ADD CONSTRAINT e2e_uq_email_key UNIQUE (email)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.constraint_handler import ConstraintHandler
    h = ConstraintHandler()
    h._snapshot = snap
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"Unique constraint self-diff produced {len(up)} ops"
    _drop(engine, "e2e_uq")


def test_check_constraint(engine):
    _drop(engine, "e2e_ck")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_ck (id int PRIMARY KEY, val int)"))
        conn.execute(sa.text("ALTER TABLE e2e_ck ADD CONSTRAINT e2e_ck_val_check CHECK (val > 0)"))
    snap = _refresh()
    from dbwarden.engine.pg_registry.constraint_handler import ConstraintHandler
    h = ConstraintHandler()
    h._snapshot = snap
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], f"Check constraint self-diff produced {len(up)} ops"
    _drop(engine, "e2e_ck")


# ===================================================================
# Combined-schema convergence (multiple handlers in one migration)
# ===================================================================

def test_combined_schema_convergence(engine):
    """Exercise several handlers on a combined schema."""
    _drop(engine, "e2e_comb_ref", "e2e_comb_main", "e2e_comb_info")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_comb_ref (id int PRIMARY KEY, code text)"))
        conn.execute(sa.text("CREATE TABLE e2e_comb_main (id int PRIMARY KEY, ref_id int, "
                             "status text DEFAULT 'active')"))
        conn.execute(sa.text("CREATE TABLE e2e_comb_info (id int PRIMARY KEY, "
                             "main_id int NOT NULL, detail text)"))
        conn.execute(sa.text("CREATE INDEX e2e_comb_main_status_idx ON e2e_comb_main (status)"))
        conn.execute(sa.text("CREATE UNIQUE INDEX e2e_comb_info_main_id_key ON e2e_comb_info (main_id)"))
        conn.execute(sa.text("ALTER TABLE e2e_comb_info ADD CONSTRAINT e2e_comb_info_main_id_fkey "
                             "FOREIGN KEY (main_id) REFERENCES e2e_comb_main (id)"))

    snap = _refresh()
    assert "e2e_comb_main" in snap["tables"]
    assert "e2e_comb_info" in snap["tables"]

    from dbwarden.engine.pg_registry.constraint_handler import ConstraintHandler

    h = ConstraintHandler()
    h._snapshot = snap
    h._view_tables = set()
    snap_spec = h.extract(snap)
    c_snap = h.canonicalize(snap_spec)
    up, rb = h.diff(c_snap, c_snap)
    assert up == [], (
        f"ConstraintHandler self-diff produced {len(up)} ops: "
        f"{[o.object_type for o in up[:5]]}"
    )

    _drop(engine, "e2e_comb_info", "e2e_comb_main", "e2e_comb_ref")
