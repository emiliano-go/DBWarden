import os

import pytest


fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dbwarden.extensions.fastapi import (
    DBWardenHealthRouter,
    check_schema_on_startup,
    migrate_on_startup,
)
from dbwarden.extensions.fastapi.runtime import HealthResult


class TestStartupHelpers:
    def test_check_schema_on_startup_only_dev_skips_outside_dev(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        called = {"value": False}

        def fake_check_startup(**_kwargs):
            called["value"] = True
            return []

        monkeypatch.setattr("dbwarden.extensions.fastapi.context.check_startup", fake_check_startup)

        result = check_schema_on_startup(only_dev=True)
        assert result == []
        assert called["value"] is False

    def test_check_schema_on_startup_raises_when_fail_fast(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")

        def fake_check_startup(**_kwargs):
            return [
                HealthResult(
                    database="primary",
                    status="error",
                    connected=False,
                    pending_migrations=0,
                    lock_active=False,
                    error="boom",
                )
            ]

        monkeypatch.setattr("dbwarden.extensions.fastapi.context.check_startup", fake_check_startup)

        with pytest.raises(RuntimeError, match="Startup check failed"):
            check_schema_on_startup(fail_fast=True)

    def test_migrate_on_startup_only_dev_skips_outside_dev(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        called = {"value": False}

        def fake_migrate_cmd(**_kwargs):
            called["value"] = True

        monkeypatch.setattr("dbwarden.extensions.fastapi.context.migrate_cmd", fake_migrate_cmd)

        migrate_on_startup(only_dev=True, allow_in_production=True)
        assert called["value"] is False

    def test_migrate_on_startup_blocks_production_without_allow(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")

        with pytest.raises(RuntimeError, match="allow_in_production=True"):
            migrate_on_startup()


class TestHealthRouter:
    def test_overall_health_ok(self, monkeypatch):
        app = FastAPI()

        def fake_check_startup(**_kwargs):
            return [
                HealthResult(
                    database="primary",
                    status="ok",
                    connected=True,
                    pending_migrations=0,
                    lock_active=False,
                    error=None,
                )
            ]

        monkeypatch.setattr("dbwarden.extensions.fastapi.health.check_startup", fake_check_startup)

        app.include_router(DBWardenHealthRouter(), prefix="/health")
        client = TestClient(app)
        response = client.get("/health/")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["databases"][0]["database"] == "primary"

    def test_single_health_404_for_unknown_database(self, monkeypatch):
        app = FastAPI()

        class FakeCfg:
            databases = {"primary": object()}

        monkeypatch.setattr("dbwarden.extensions.fastapi.health.get_multi_db_config", lambda: FakeCfg())
        app.include_router(DBWardenHealthRouter(), prefix="/health")
        client = TestClient(app)

        response = client.get("/health/unknown")
        assert response.status_code == 404

    def test_liveness_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import DBWardenHealthRouter

        app = FastAPI()
        app.include_router(DBWardenHealthRouter(), prefix="/health")
        client = TestClient(app)

        resp = client.get("/health/liveness")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_readiness_endpoint(self, monkeypatch):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import DBWardenHealthRouter

        app = FastAPI()

        class FakeResult:
            status = "ok"
            database = "primary"
            connected = True
            error = None
            pending_migrations = 0
            applied_migrations = 5
            pending_seeds = 0
            applied_seeds = 1
            lock_active = False

            def to_database_health(self):
                from dbwarden.extensions.fastapi.types import DatabaseHealth
                return DatabaseHealth(
                    database=self.database, status=self.status,
                    connected=self.connected, pending_migrations=self.pending_migrations,
                    applied_migrations=self.applied_migrations, pending_seeds=self.pending_seeds,
                    applied_seeds=self.applied_seeds, lock_active=self.lock_active, error=self.error,
                )

        def fake_check(**kw):
            return [FakeResult()]

        def fake_cfg():
            class Cfg:
                databases = {"primary": object()}
            return Cfg()

        monkeypatch.setattr("dbwarden.extensions.fastapi.health.check_startup", fake_check)
        monkeypatch.setattr("dbwarden.extensions.fastapi.health.get_multi_db_config", fake_cfg)

        app.include_router(DBWardenHealthRouter(), prefix="/health")
        client = TestClient(app)
        resp = client.get("/health/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["databases"]) == 1

    def test_liveness_auth_required(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import DBWardenHealthRouter

        app = FastAPI()
        app.include_router(DBWardenHealthRouter(auth_mode="authenticated", api_key="secret"), prefix="/health")
        client = TestClient(app)

        assert client.get("/health/liveness").status_code == 401
        assert client.get("/health/liveness", headers={"X-API-Key": "wrong"}).status_code == 403
        assert client.get("/health/liveness", headers={"X-API-Key": "secret"}).status_code == 200
