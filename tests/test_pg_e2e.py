"""End-to-end validation of all PGSQL handlers against a real PG 13 server.

Prerequisites:
    docker run -d --name pg13-e2e -e POSTGRES_PASSWORD=postgres \\
        -e POSTGRES_DB=dbwarden_test -p 15432:5432 postgres:13-alpine

Run:
    DBWARDEN_E2E=1 python -m pytest tests/test_pg_e2e.py -v --timeout 120
"""

import os
import sqlalchemy as sa
import pytest

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


@pytest.fixture(scope="module")
def snap(engine):
    from dbwarden.engine.snapshot import extract_full_schema_snapshot
    return extract_full_schema_snapshot(
        sqlalchemy_url=PG_URL,
        database_type="postgresql",
    )


# ---------------------------------------------------------------------------
# PartitionHandler
# ---------------------------------------------------------------------------

def test_partition_extraction(engine, snap):
    _drop("e2e_part_child", "e2e_part_parent")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_part_parent (id int, created_at date) PARTITION BY RANGE (created_at)"))
        conn.execute(sa.text("CREATE TABLE e2e_part_child PARTITION OF e2e_part_parent "
                             "FOR VALUES FROM ('2024-01-01') TO ('2025-01-01')"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry import PartitionHandler
    spec = PartitionHandler().extract(fresh)
    assert "e2e_part_parent" in spec, f"parent not found in {list(spec.keys())}"
    entry = spec["e2e_part_parent"]
    assert entry.get("pg_partition") == {"strategy": "RANGE", "columns": ["created_at"]}, entry.get("pg_partition")
    children = entry.get("pg_partitions", [])
    assert len(children) == 1
    assert children[0]["name"] == "e2e_part_child"
    assert "2024-01-01" in children[0]["bound"]

    _drop("e2e_part_child", "e2e_part_parent")


# ---------------------------------------------------------------------------
# FunctionHandler
# ---------------------------------------------------------------------------

def test_function_extraction(engine, snap):
    _drop("e2e_hello")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE OR REPLACE FUNCTION e2e_hello() RETURNS text "
                             "LANGUAGE sql AS $$ SELECT 'hello'::text $$"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry import FunctionHandler
    spec = FunctionHandler().extract(fresh)
    assert "e2e_hello" in spec, f"e2e_hello not found in {list(spec.keys())}"
    entry = spec["e2e_hello"]
    assert "definition" in entry
    assert "e2e_hello" in entry["definition"]

    _drop("e2e_hello")


# ---------------------------------------------------------------------------
# TriggerHandler
# ---------------------------------------------------------------------------

def test_trigger_extraction(engine, snap):
    _drop("e2e_trigger_target", "e2e_trg_func")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_trigger_target (id int, name text)"))
        conn.execute(sa.text("CREATE OR REPLACE FUNCTION e2e_trg_func() RETURNS trigger "
                             "LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$"))
        conn.execute(sa.text("CREATE TRIGGER e2e_trg BEFORE INSERT ON e2e_trigger_target "
                             "FOR EACH ROW EXECUTE FUNCTION e2e_trg_func()"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry import TriggerHandler
    spec = TriggerHandler().extract(fresh)
    assert "e2e_trigger_target" in spec
    trigs = spec["e2e_trigger_target"]
    assert "e2e_trg" in trigs
    assert "definition" in trigs["e2e_trg"]
    assert "e2e_trg" in trigs["e2e_trg"]["definition"]

    _drop("e2e_trigger_target", "e2e_trg_func")


# ---------------------------------------------------------------------------
# RoleHandler
# ---------------------------------------------------------------------------

def test_role_extraction(engine, snap):
    from dbwarden.engine.pg_registry import RoleHandler
    spec = RoleHandler().extract(snap)
    assert "postgres" in spec  # superuser role is visible
    assert "pg_execute_server_programs" not in spec  # starts with pg_ is excluded
    assert isinstance(spec, dict)


# ---------------------------------------------------------------------------
# DomainHandler (existing, confirm stable)
# ---------------------------------------------------------------------------

def test_domain_extraction(engine, snap):
    from dbwarden.engine.pg_registry import DomainHandler
    spec = DomainHandler().extract(snap)
    assert isinstance(spec, dict)


# ---------------------------------------------------------------------------
# EnumHandler (existing, confirm stable)
# ---------------------------------------------------------------------------

def test_enum_extraction(engine, snap):
    from dbwarden.engine.pg_registry import EnumHandler
    spec = EnumHandler().extract(snap)
    assert isinstance(spec, dict)


# ---------------------------------------------------------------------------
# Sequences (existing, confirm stable)
# ---------------------------------------------------------------------------

def test_sequence_extraction(engine, snap):
    from dbwarden.engine.pg_registry import SequenceHandler
    spec = SequenceHandler().extract(snap)
    assert isinstance(spec, dict)


# ---------------------------------------------------------------------------
# CompositeTypeHandler
# ---------------------------------------------------------------------------

def test_composite_type_extraction(engine, snap):
    _drop("e2e_comp")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TYPE e2e_comp AS (a int, b text)"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry import CompositeTypeHandler
    spec = CompositeTypeHandler().extract(fresh)
    assert "e2e_comp" in spec, f"e2e_comp not found in {list(spec.keys())}"
    entry = spec["e2e_comp"]
    assert "columns" in entry
    cols = entry["columns"]
    assert any(c["name"] == "a" and "int" in c["type"] for c in cols)
    assert any(c["name"] == "b" and "text" in c["type"] for c in cols)

    _drop("e2e_comp")


# ---------------------------------------------------------------------------
# StatisticsHandler
# ---------------------------------------------------------------------------

def test_statistics_extraction(engine, snap):
    _drop("e2e_stat_test")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_stat_test (id int, val int)"))
        conn.execute(sa.text("ALTER TABLE e2e_stat_test ALTER COLUMN val SET STATISTICS 42"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry import StatisticsHandler
    spec = StatisticsHandler().extract(fresh)
    assert "e2e_stat_test" in spec, f"e2e_stat_test not found in {list(spec.keys())}"
    assert spec["e2e_stat_test"].get("val") == 42

    _drop("e2e_stat_test")


def test_extended_statistics_extraction(engine, snap):
    _drop("e2e_stats")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_stats (id int, a int, b int, c int)"))
        conn.execute(sa.text("INSERT INTO e2e_stats SELECT x, x, x*2, x*3 FROM generate_series(1, 1000) x"))
        conn.execute(sa.text("ANALYZE e2e_stats"))
        conn.execute(sa.text("CREATE STATISTICS e2e_s1 (dependencies) ON a, b FROM e2e_stats"))
        conn.execute(sa.text("CREATE STATISTICS e2e_s2 (ndistinct) ON a, b, c FROM e2e_stats"))
        conn.execute(sa.text("CREATE STATISTICS e2e_s3 ON a, b FROM e2e_stats"))

    fresh = _refresh()
    from dbwarden.engine.pg_registry.extended_statistics_handler import ExtendedStatisticsHandler
    spec = ExtendedStatisticsHandler().extract(fresh)
    assert "e2e_s1" in spec, f"e2e_s1 not found in {list(spec.keys())}"
    assert "e2e_s2" in spec, f"e2e_s2 not found in {list(spec.keys())}"
    assert "e2e_s3" in spec, f"e2e_s3 not found in {list(spec.keys())}"

    s1 = spec["e2e_s1"]
    assert s1["table"] == "e2e_stats"
    assert "f" in s1["kinds"]
    assert s1["columns"] is not None

    s3 = spec["e2e_s3"]
    assert set(s3["kinds"]) == {"d", "f", "m"}

    _drop("e2e_stats")


def test_event_trigger_extraction(engine, snap):
    _drop("e2e_evt_trg", "e2e_evt_func")
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION e2e_evt_func()
            RETURNS event_trigger AS $$ BEGIN END; $$ LANGUAGE plpgsql
        """))
        conn.execute(sa.text("""
            CREATE EVENT TRIGGER e2e_evt_trg ON ddl_command_start
            WHEN TAG IN ('CREATE TABLE')
            EXECUTE FUNCTION e2e_evt_func()
        """))

    fresh = _refresh()
    from dbwarden.engine.pg_registry.event_trigger_handler import EventTriggerHandler
    spec = EventTriggerHandler().extract(fresh)
    assert "e2e_evt_trg" in spec, f"e2e_evt_trg not found in {list(spec.keys())}"
    entry = spec["e2e_evt_trg"]
    assert entry["event"] == "ddl_command_start"
    assert "CREATE TABLE" in entry.get("tags", [])
    assert entry["function"]["name"] == "e2e_evt_func"

    _drop("e2e_evt_trg", "e2e_evt_func")


def test_schema_grant_extraction(engine, snap):
    _drop("e2e_sg_schema")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE SCHEMA e2e_sg_schema"))
        conn.execute(sa.text("GRANT USAGE, CREATE ON SCHEMA e2e_sg_schema TO PUBLIC"))

    fresh = _refresh()
    sg = fresh.get("schema_grants", {})
    assert "e2e_sg_schema" in sg, f"e2e_sg_schema not found in {list(sg.keys())}"
    entries = sg["e2e_sg_schema"]
    any_public = any(e["role"] == "PUBLIC" for e in entries)
    assert any_public, f"PUBLIC grant not found in {entries}"

    with engine.begin() as conn:
        conn.execute(sa.text("DROP SCHEMA e2e_sg_schema CASCADE"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refresh():
    from dbwarden.engine.snapshot import extract_full_schema_snapshot
    return extract_full_schema_snapshot(
        sqlalchemy_url=PG_URL,
        database_type="postgresql",
    )


def _drop(*names):
    e = sa.create_engine(PG_URL)
    with e.begin() as conn:
        for n in names:
            for tmpl in (
                "DROP TABLE IF EXISTS {n} CASCADE",
                "DROP FUNCTION IF EXISTS {n} CASCADE",
                "DROP TYPE IF EXISTS {n} CASCADE",
                "DROP STATISTICS IF EXISTS {n} CASCADE",
                "DROP EVENT TRIGGER IF EXISTS {n} CASCADE",
                "DROP SCHEMA IF EXISTS {n} CASCADE",
            ):
                try:
                    conn.execute(sa.text(tmpl.format(n=n)))
                except Exception:
                    pass
    e.dispose()
