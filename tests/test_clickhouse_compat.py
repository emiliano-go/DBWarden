import base64
import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib import request as urllib_request

import pytest
from sqlalchemy import create_engine, text

from dbwarden.commands.make_migrations import make_migrations_cmd
from dbwarden.commands.migrate import migrate_cmd
from dbwarden.repositories import (
    create_lock_table_if_not_exists,
    create_migrations_table_if_not_exists,
    get_migration_records,
    migrations_table_exists,
    run_migration,
)


SKIP_CLICKHOUSE_TESTS = os.environ.get("DBWARDEN_SKIP_CLICKHOUSE_TESTS") == "1"
CUSTOM_BASE_URL = os.environ.get("DBWARDEN_CLICKHOUSE_BASE_URL")
CLICKHOUSE_TEST_USER = os.environ.get("DBWARDEN_CLICKHOUSE_USER", "dbwarden")
CLICKHOUSE_TEST_PASSWORD = os.environ.get("DBWARDEN_CLICKHOUSE_PASSWORD", "dbwarden")
DOCKER_AVAILABLE = shutil.which("docker") is not None

if SKIP_CLICKHOUSE_TESTS or (CUSTOM_BASE_URL is None and not DOCKER_AVAILABLE):
    reason = "ClickHouse tests skipped"
    if SKIP_CLICKHOUSE_TESTS:
        reason = "ClickHouse tests disabled via DBWARDEN_SKIP_CLICKHOUSE_TESTS"
    elif CUSTOM_BASE_URL is None and not DOCKER_AVAILABLE:
        reason = "Docker is required to run ClickHouse tests"
    pytestmark = pytest.mark.skip(reason=reason)


def _wait_for_clickhouse(
    host: str = "127.0.0.1", port: int = 8123, timeout: int = 90
) -> None:
    deadline = time.time() + timeout
    url = f"http://{host}:{port}/?query=SELECT%201"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            request = urllib_request.Request(url)
            auth_bytes = f"{CLICKHOUSE_TEST_USER}:{CLICKHOUSE_TEST_PASSWORD}".encode()
            auth_header = base64.b64encode(auth_bytes).decode()
            request.add_header("Authorization", f"Basic {auth_header}")
            with urllib_request.urlopen(request, timeout=2):
                return
        except Exception as exc:  # pragma: no cover - best effort logging
            last_error = exc
            time.sleep(1)
    if last_error:
        raise RuntimeError(
            f"ClickHouse server did not become ready in time (last error: {last_error})"
        ) from last_error
    raise RuntimeError("ClickHouse server did not become ready in time")


def _get_free_port(exclude: set[int] | None = None) -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            port = sock.getsockname()[1]
        if not exclude or port not in exclude:
            return port


@pytest.fixture(scope="session")
def clickhouse_base_url():
    if CUSTOM_BASE_URL:
        yield CUSTOM_BASE_URL.rstrip("/")
        return

    container_name = f"dbwarden-clickhouse-{uuid.uuid4().hex[:8]}"
    used_ports: set[int] = set()
    http_port = _get_free_port()
    used_ports.add(http_port)
    native_port = _get_free_port(used_ports)
    container_started = False
    run_args = [
        "docker",
        "run",
        "-d",
        "--rm",
        "-e",
        f"CLICKHOUSE_USER={CLICKHOUSE_TEST_USER}",
        "-e",
        f"CLICKHOUSE_PASSWORD={CLICKHOUSE_TEST_PASSWORD}",
        "-p",
        f"{http_port}:8123",
        "-p",
        f"{native_port}:9000",
        "--name",
        container_name,
        "clickhouse/clickhouse-server:24.8",
    ]
    try:
        subprocess.run(run_args, check=True, capture_output=True)
        container_started = True
        _wait_for_clickhouse(port=http_port)
        yield (
            f"clickhousedb+connect://{CLICKHOUSE_TEST_USER}:{CLICKHOUSE_TEST_PASSWORD}"
            f"@127.0.0.1:{http_port}"
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"").decode("utf-8", "ignore").strip()
        pytest.skip(f"Unable to start ClickHouse container: {stderr}")
    except RuntimeError as exc:
        pytest.skip(f"ClickHouse container did not become ready: {exc}")
    finally:
        if container_started:
            subprocess.run(
                ["docker", "stop", container_name], check=False, capture_output=True
            )


@pytest.fixture
def clickhouse_env(tmp_path, clickhouse_base_url):
    db_name = f"dbwarden_test_{uuid.uuid4().hex[:6]}"
    admin_engine = create_engine(f"{clickhouse_base_url}/default")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
    admin_engine.dispose()

    config_path = tmp_path / "warden.toml"
    config_path.write_text(
        'database_type = "clickhouse"\n'
        f'sqlalchemy_url = "{clickhouse_base_url}/{db_name}"\n'
        'model_paths = ["./models"]\n',
        encoding="utf-8",
    )

    previous_cwd = os.getcwd()
    os.chdir(tmp_path)

    yield {
        "db_name": db_name,
        "database_url": f"{clickhouse_base_url}/{db_name}",
        "base_url": clickhouse_base_url,
    }

    os.chdir(previous_cwd)
    admin_engine = create_engine(f"{clickhouse_base_url}/default")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
    admin_engine.dispose()


def test_clickhouse_tracking_tables(clickhouse_env):
    create_migrations_table_if_not_exists()
    create_lock_table_if_not_exists()

    assert migrations_table_exists() is True


def test_clickhouse_runs_merge_tree_migration(clickhouse_env):
    create_migrations_table_if_not_exists()
    merge_tree_sql = [
        """
        CREATE TABLE IF NOT EXISTS events (
            event_date Date DEFAULT today(),
            event_id UInt64,
            value String
        )
        ENGINE = MergeTree()
        ORDER BY (event_date, event_id)
        """.strip()
    ]

    run_migration(
        sql_statements=merge_tree_sql,
        version="1",
        migration_operation="upgrade",
        filename="V1__events.sql",
    )

    records = get_migration_records()
    assert len(records) == 1
    assert records[0].version == "1"

    engine = create_engine(clickhouse_env["database_url"])
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT engine FROM system.tables
                WHERE database = currentDatabase() AND name = 'events'
                """
            )
        )
        engine_name = result.scalar_one()

    assert engine_name.lower() == "mergetree"


def test_clickhouse_make_migrations_from_models(clickhouse_env):
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    models_file = models_dir / "click_models.py"
    models_file.write_text(
        """
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ClickEvent(Base):
    __tablename__ = "click_events"
    __table_args__ = {
        "info": {
            "clickhouse_engine": "ReplacingMergeTree()",
            "clickhouse_order_by": "(event_id)",
            "clickhouse_partition_by": "toYYYYMM(occurred_at)",
            "clickhouse_settings": {"index_granularity": 128}
        }
    }

    event_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    payload = Column(String(255))
    occurred_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True)
    message = Column(String(255))
    created_at = Column(DateTime, nullable=False)
""",
        encoding="utf-8",
    )

    Path("migrations").mkdir(exist_ok=True)

    make_migrations_cmd(description="clickhouse_models", verbose=True)

    migration_files = sorted(Path("migrations").glob("*.sql"))
    assert migration_files, "Expected migration file to be generated"
    migration_content = migration_files[-1].read_text(encoding="utf-8")
    assert "ENGINE = ReplacingMergeTree()" in migration_content
    assert "UInt8" in migration_content
    assert "ORDER BY (event_id)" in migration_content

    migrate_cmd(verbose=True)

    engine = create_engine(clickhouse_env["database_url"])
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                """
                SELECT name, engine, sorting_key
                FROM system.tables
                WHERE database = currentDatabase()
                  AND name IN ('click_events', 'audit_logs')
                ORDER BY name
                """
            )
        ).fetchall()

        assert {row.name for row in tables} == {"audit_logs", "click_events"}
        click_events = next(row for row in tables if row.name == "click_events")
        assert "ReplacingMergeTree" in click_events.engine
        assert "event_id" in click_events.sorting_key

        columns = conn.execute(
            text(
                """
                SELECT table, name, type
                FROM system.columns
                WHERE database = currentDatabase()
                  AND table IN ('click_events', 'audit_logs')
                """
            )
        ).fetchall()

    column_types = {(row.table, row.name): row.type for row in columns}
    assert column_types[("click_events", "is_active")] == "UInt8"
    assert column_types[("audit_logs", "log_id")] == "Int32"
