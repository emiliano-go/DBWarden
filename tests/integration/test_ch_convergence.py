"""Two-cycle convergence test against a live ClickHouse server.

Usage::

    pytest tests/integration/ --ch-integration --tb=short -v

Environment variables (for CI service containers)::

    CLICKHOUSE_HOST    (default: localhost)
    CLICKHOUSE_PORT    (default: 8123 for HTTP, 9000 for native)
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("testcontainers.clickhouse")
pytest.importorskip("clickhouse_connect")

from dbwarden.engine.core.models import ModelColumn, ModelTable


def _get_ch_client():
    """Return a clickhouse-connect client."""
    import clickhouse_connect

    host = os.environ.get("CLICKHOUSE_HOST")
    native_port = os.environ.get("CLICKHOUSE_PORT")
    if host and native_port:
        return clickhouse_connect.get_client(
            host=host,
            port=int(native_port),
            username=os.environ.get("CLICKHOUSE_USERNAME", "default"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
        )

    from testcontainers.clickhouse import ClickHouseContainer

    ch = ClickHouseContainer(image="clickhouse/clickhouse-server:24.3")
    ch.__enter__()
    client = clickhouse_connect.get_client(
        host=ch.get_container_host_ip(),
        port=ch.get_exposed_port(8123),
        username=ch.username,
        password=ch.password,
    )
    client._dbw_container = ch
    return client


def _extract_opts(client, table_name: str, database: str = "dbw_test") -> dict:
    """Query system.tables via clickhouse-connect and build an options dict."""
    rows = client.query(
        "SELECT engine, engine_full, sorting_key, primary_key, "
        "partition_key, sampling_key, create_table_query "
        "FROM system.tables WHERE database = %(db)s AND name = %(name)s",
        parameters={"db": database, "name": table_name},
    )
    if not rows.result_rows:
        return {}
    row = rows.result_rows[0]

    from dbwarden.engine.backends.clickhouse.parse import (
        parse_tuple_or_list as _parse_tuple_or_list,
        _clean_expression,
        parse_ttl_expressions as _parse_ttl_expressions,
        parse_projection_queries as _parse_projection_queries,
        parse_mv_query as _parse_mv_query,
        parse_zookeeper_path as _parse_zookeeper_path,
        parse_replica_name as _parse_replica_name,
    )
    from dbwarden.databases.clickhouse.engine import ChEngineSpec

    engine = row[0] or ""
    engine_full = row[1] or ""
    create_query = row[6] or ""

    options: dict = {}

    if engine_full:
        _raw = _clean_ch_engine_full(engine_full)
        options["ch_engine_raw"] = ChEngineSpec.from_engine_string(_raw)
    elif engine:
        options["ch_engine_raw"] = ChEngineSpec.from_engine_string(engine)
    options["ch_engine"] = engine

    sorting_key = _parse_tuple_or_list(row[2])
    if sorting_key:
        options["ch_order_by"] = sorting_key if isinstance(sorting_key, list) else [sorting_key]
    primary_key = _parse_tuple_or_list(row[3])
    if primary_key:
        options["ch_primary_key"] = primary_key if isinstance(primary_key, list) else [primary_key]
    partition_key = _clean_expression(row[4])
    if partition_key:
        options["ch_partition_by"] = partition_key
    sampling_key = _clean_expression(row[5])
    if sampling_key:
        options["ch_sample_by"] = sampling_key

    ttl = _parse_ttl_expressions(create_query)
    if ttl:
        options["ch_ttl"] = ttl

    projections = _parse_projection_queries(create_query)
    if projections:
        options["ch_projections"] = projections

    mv_query = _parse_mv_query(create_query)
    if mv_query:
        options["ch_select_statement"] = mv_query
        options["ch_object_type"] = "materialized_view"

    zk_path = _parse_zookeeper_path(create_query, engine)
    if zk_path:
        options["ch_zookeeper_path"] = zk_path
    replica = _parse_replica_name(create_query, engine)
    if replica:
        options["ch_replica_name"] = replica

    if engine.upper() == "DICTIONARY":
        options["ch_dictionary"] = True
        options["ch_object_type"] = "dictionary"

    if create_query.strip().upper().startswith("CREATE MATERIALIZED VIEW"):
        options["ch_object_type"] = "materialized_view"

    from dbwarden.engine.backends.clickhouse.parse import (
        parse_settings as _parse_settings,
    )
    settings = _parse_settings(create_query)
    if settings:
        options["ch_settings"] = settings

    return options


def _clean_ch_engine_full(engine_full: str) -> str:
    idx = engine_full.find("(")
    if idx == -1:
        return engine_full
    depth = 0
    for i, c in enumerate(engine_full[idx:], start=idx):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return engine_full[:i + 1]
    return engine_full


@pytest.mark.integration
class TestClickHouseConvergence:
    """Live ClickHouse convergence test — mark with ``--ch-integration``."""

    @pytest.fixture(scope="class")
    def ch_client(self):
        client = _get_ch_client()
        yield client
        container = getattr(client, "_dbw_container", None)
        if container is not None:
            container.__exit__(None, None, None)

    def _create_tables(self, client):
        client.command("CREATE DATABASE IF NOT EXISTS dbw_test")
        client.command("DROP TABLE IF EXISTS dbw_test.events")
        client.command("""
            CREATE TABLE dbw_test.events (
                id UInt64,
                user_id Int64,
                event_time DateTime,
                amount Float64,
                payload String CODEC(ZSTD(3))
            ) ENGINE = MergeTree()
            ORDER BY (user_id, event_time)
            PARTITION BY toYYYYMM(event_time)
            TTL event_time + INTERVAL 90 DAY
            SETTINGS index_granularity = 8192
        """)

    def test_merge_tree_table_converges(self, ch_client):
        self._create_tables(ch_client)

        opts = _extract_opts(ch_client, "events")
        assert opts.get("ch_engine"), f"No ch_engine: {opts}"
        assert opts.get("ch_order_by"), f"No ch_order_by: {opts}"

        mt = ModelTable(
            name="events",
            columns=[
                ModelColumn("id", "UInt64", False, True, False, None, None,
                            ch_meta={"ch_type": "UInt64"}),
                ModelColumn("user_id", "Int64", False, False, False, None, None,
                            ch_meta={"ch_type": "Int64"}),
                ModelColumn("event_time", "DateTime", False, False, False, None, None,
                            ch_meta={"ch_type": "DateTime"}),
                ModelColumn("amount", "Float64", False, False, False, None, None,
                            ch_meta={"ch_type": "Float64"}),
                ModelColumn("payload", "String", False, False, False, None, None,
                            ch_meta={"ch_type": "String", "ch_codec": "ZSTD(3)"}),
            ],
            clickhouse_options={
                "ch_engine": "MergeTree",
                "ch_order_by": ("user_id", "event_time"),
                "ch_partition_by": "toYYYYMM(event_time)",
                "ch_ttl": ["event_time + toIntervalDay(90)"],
                "ch_settings": {"index_granularity": "8192"},
            },
        )

        from dbwarden.engine.backends.clickhouse.handlers import ChTableHandler, ChColumnHandler

        # --- Cycle 1: extract → model → diff → must be empty ---
        th = ChTableHandler()
        snap = {"events": {
            "ch_options": dict(opts),
            "snapshot_table": {"name": "events", "columns": {}},
        }}
        model = {"events": {
            "ch_options": dict(mt.clickhouse_options),
            "model_table": mt,
        }}
        up, _ = th.diff(snap, model)
        assert not up, f"Cycle 1 (table options) drift: {up}"

        # --- Column handler ---
        ch = ChColumnHandler()
        snap_cols = ch.extract({"tables": {"events": {
            "ch_options": opts, "columns": {c.name: {
                "ch_column": (c.ch_meta or {})
            } for c in mt.columns},
        }}})
        model_cols = ch.model_spec_from_tables([mt])
        up_cols, _ = ch.diff(snap_cols, model_cols)
        assert not up_cols, f"Cycle 1 (column meta) drift: {up_cols}"

        # --- Cycle 2: same data, same result ---
        up2, _ = th.diff(snap, model)
        assert not up2, f"Cycle 2 (table options) drift: {up2}"
        up_cols2, _ = ch.diff(snap_cols, model_cols)
        assert not up_cols2, f"Cycle 2 (column meta) drift: {up_cols2}"

    @pytest.mark.skip(reason="no ZooKeeper/keeper in default testcontainers ClickHouse image; ReplicatedMergeTree extraction (zookeeper_path/replica_name parse) is the uncovered path — CH 24.3+ ships embedded clickhouse-keeper via config mount if needed")
    def test_replicated_merge_tree_converges(self, ch_client):
        self._create_tables(ch_client)
