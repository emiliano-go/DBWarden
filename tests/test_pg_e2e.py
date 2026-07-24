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
    from dbwarden.engine.backends.postgresql.handlers import PartitionHandler
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
# StatisticsHandler
# ---------------------------------------------------------------------------

def test_statistics_extraction(engine, snap):
    _drop("e2e_stat_test")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE e2e_stat_test (id int, val int)"))
        conn.execute(sa.text("ALTER TABLE e2e_stat_test ALTER COLUMN val SET STATISTICS 42"))

    fresh = _refresh()
    from dbwarden.engine.backends.postgresql.handlers import StatisticsHandler
    spec = StatisticsHandler().extract(fresh)
    assert "e2e_stat_test" in spec, f"e2e_stat_test not found in {list(spec.keys())}"
    assert spec["e2e_stat_test"].get("val") == 42

    _drop("e2e_stat_test")


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
