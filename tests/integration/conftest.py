"""Integration test fixtures for database containers."""

def pytest_addoption(parser):
    parser.addoption(
        "--ch-integration",
        action="store_true",
        default=False,
        help="Run ClickHouse integration tests that require a live container",
    )
    parser.addoption(
        "--ch-image",
        action="store",
        default="clickhouse/clickhouse-server:24.3",
        help="ClickHouse Docker image tag for integration tests",
    )
    parser.addoption(
        "--pg-integration",
        action="store_true",
        default=False,
        help="Run PostgreSQL integration tests that require a live container",
    )
