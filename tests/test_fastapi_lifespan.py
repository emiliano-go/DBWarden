import pytest

pytest.importorskip("fastapi")


class TestQueryTracingMiddleware:
    def test_middleware_applied(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import QueryTracingMiddleware

        app = FastAPI()
        app.add_middleware(QueryTracingMiddleware, slow_query_threshold_ms=50)

        @app.get("/test")
        async def handler():
            return {"ok": True}

        resp = TestClient(app).get("/test")
        assert resp.status_code == 200

    def test_middleware_passthrough_non_http(self):
        from dbwarden.extensions.fastapi import QueryTracingMiddleware

        async def noop_app(scope, receive, send):
            await send({"type": "websocket.send", "text": "ok"})

        middleware = QueryTracingMiddleware(noop_app)
        assert middleware.slow_query_threshold_ms == 100


class TestPoolMetricsCollector:
    def test_collect_returns_metrics(self):
        from sqlalchemy import create_engine
        from dbwarden.extensions.fastapi import PoolMetricsCollector

        collector = PoolMetricsCollector()
        engine = create_engine("sqlite:///:memory:")
        collector.register("test_db", engine)
        metrics = collector.collect()
        assert "test_db" in metrics
        assert metrics["test_db"]["pool_size"] >= 0
        assert metrics["test_db"]["checked_out"] >= 0
        assert metrics["test_db"]["overflow"] >= 0

    def test_empty_collector(self):
        from dbwarden.extensions.fastapi import PoolMetricsCollector
        assert PoolMetricsCollector().collect() == {}

    def test_multiple_engines(self):
        from sqlalchemy import create_engine
        from dbwarden.extensions.fastapi import PoolMetricsCollector

        collector = PoolMetricsCollector()
        collector.register("a", create_engine("sqlite:///:memory:"))
        collector.register("b", create_engine("sqlite:///:memory:"))
        metrics = collector.collect()
        assert set(metrics.keys()) == {"a", "b"}


class TestOverrideDatabase:
    @pytest.mark.asyncio
    async def test_override_and_restore(self, monkeypatch):
        from dbwarden.config import DatabaseConfig
        from dbwarden.extensions.fastapi.testing import override_database

        mock_config = DatabaseConfig(
            database_type="sqlite",
            sqlalchemy_url_sync="sqlite:///:memory:",
        )
        monkeypatch.setattr("dbwarden.config.get_database", lambda db=None: mock_config)
        monkeypatch.setattr("dbwarden.config.get_multi_db_config", lambda: type("obj", (object,), {"default": "test_ovr"})())

        orig = mock_config.sqlalchemy_url_sync
        assert orig == "sqlite:///:memory:"
        async with override_database("test_ovr", "sqlite:///./_tmp_ovr.db"):
            assert mock_config.sqlalchemy_url_sync == "sqlite:///./_tmp_ovr.db"
        assert mock_config.sqlalchemy_url_sync == "sqlite:///:memory:"

        import os
        try:
            os.remove("./_tmp_ovr.db")
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_override_restores_on_error(self, monkeypatch):
        from dbwarden.config import DatabaseConfig
        from dbwarden.extensions.fastapi.testing import override_database

        mock_config = DatabaseConfig(
            database_type="sqlite",
            sqlalchemy_url_sync="sqlite:///:memory:",
        )
        monkeypatch.setattr("dbwarden.config.get_database", lambda db=None: mock_config)
        monkeypatch.setattr("dbwarden.config.get_multi_db_config", lambda: type("obj", (object,), {"default": "test_ovr"})())

        original = mock_config.sqlalchemy_url_sync
        try:
            async with override_database("test_ovr", "sqlite:///./_tmp_err.db"):
                raise ValueError("test error")
        except ValueError:
            pass
        assert mock_config.sqlalchemy_url_sync == original

        import os
        try:
            os.remove("./_tmp_err.db")
        except OSError:
            pass


class TestMigrationState:
    def test_migration_state_can_be_instantiated(self):
        from dbwarden.extensions.fastapi import migration_state
        assert migration_state is not None


class TestDBWardenLifespan:
    def test_readiness_gate_raises_on_bad_db(self, monkeypatch):
        from dbwarden.extensions.fastapi.lifespan import _check_readiness

        class MockResult:
            status = "error"

        def mock_health(name):
            return MockResult()

        monkeypatch.setattr("dbwarden.extensions.fastapi.runtime.check_database_health", mock_health)
        monkeypatch.setattr("dbwarden.extensions.fastapi.runtime.resolved_databases", lambda all_databases=False, database=None: ["bad_db"])

        import pytest
        with pytest.raises(RuntimeError, match="Readiness gate failed"):
            _check_readiness(database="bad_db")

    def test_warmup_pools_does_not_crash(self):
        from dbwarden.extensions.fastapi.lifespan import _warmup_pools
        _warmup_pools(database="test_ovr", size=1)
