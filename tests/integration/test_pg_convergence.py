"""Two-cycle convergence test against a live PostgreSQL server.

Usage::

    pytest tests/integration/ --pg-integration --tb=short -v

Environment variables (for CI service containers)::

    PG_HOST       (default: localhost)
    PG_PORT       (default: 5432)
    PG_USER       (default: postgres)
    PG_PASSWORD   (default: postgres)
    PG_DATABASE   (default: dbwarden_test)
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("testcontainers.postgres")
pytest.importorskip("sqlalchemy")


def _get_pg_url() -> str:
    """Return a PostgreSQL URL from env vars or start a testcontainer."""
    host = os.environ.get("PG_HOST")
    port = os.environ.get("PG_PORT")
    if host and port:
        user = os.environ.get("PG_USER", "postgres")
        password = os.environ.get("PG_PASSWORD", "postgres")
        database = os.environ.get("PG_DATABASE", "dbwarden_test")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    from testcontainers.postgres import PostgresContainer

    pg = PostgresContainer("postgres:13-alpine")
    pg.__enter__()
    url = pg.get_connection_url().replace("+psycopg2", "")
    pg._dbw_url = url
    return url


@pytest.mark.integration
class TestPostgreSQLConvergence:
    """Live PostgreSQL convergence test — mark with ``--pg-integration``."""

    @pytest.fixture(scope="class")
    def pg_url(self):
        url = _get_pg_url()
        yield url
        from testcontainers.core.container import DockerContainer

        for obj in list(globals().values()):
            if isinstance(obj, DockerContainer) and hasattr(obj, "_dbw_url"):
                obj.__exit__(None, None, None)

    def _create_test_table(self, engine):
        import sqlalchemy as sa

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS dbw_pg_events CASCADE"))
            conn.execute(sa.text("""
                CREATE TABLE dbw_pg_events (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_time TIMESTAMP NOT NULL DEFAULT NOW(),
                    amount NUMERIC(12, 2),
                    payload TEXT
                )
            """))

    def test_snapshot_cycle_converges(self, pg_url):
        """Extract snapshot from live PG, then run a drift check against itself."""
        import sqlalchemy as sa

        from dbwarden.engine.snapshot import extract_full_schema_snapshot

        engine = sa.create_engine(pg_url)
        self._create_test_table(engine)

        snap = extract_full_schema_snapshot(
            sqlalchemy_url=pg_url,
            database_type="postgresql",
        )
        assert "dbw_pg_events" in snap.get("tables", {}), (
            f"dbw_pg_events not in snapshot: {list(snap.get('tables', {}).keys())}"
        )

        from dbwarden.engine.backends.postgresql.handlers import (
            ColumnHandler,
            PgTableHandler,
        )

        th = PgTableHandler()
        col_h = ColumnHandler()

        snap_spec = th.extract(snap)
        assert "dbw_pg_events" in snap_spec, (
            f"PgTableHandler.extract missing table: {list(snap_spec.keys())}"
        )

        snap_cols = col_h.extract(snap)
        assert "dbw_pg_events" in snap_cols, (
            f"ColumnHandler.extract missing table: {list(snap_cols.keys())}"
        )

        # Cycle 1: diff snap against itself -> zero drift
        up1, _ = th.diff(snap_spec, snap_spec)
        assert not up1, f"Cycle 1 (table) drift against self: {up1}"

        up_cols1, _ = col_h.diff(snap_cols, snap_cols)
        assert not up_cols1, f"Cycle 1 (columns) drift against self: {up_cols1}"

        # Cycle 2: same data, same result
        up2, _ = th.diff(snap_spec, snap_spec)
        assert not up2, f"Cycle 2 (table) drift against self: {up2}"

        up_cols2, _ = col_h.diff(snap_cols, snap_cols)
        assert not up_cols2, f"Cycle 2 (columns) drift against self: {up_cols2}"

        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS dbw_pg_events CASCADE"))
