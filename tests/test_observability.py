"""Tests for observability features: Prometheus metrics."""

import re

import pytest


class TestMetricsModule:
    """Tests for dbwarden.metrics: Prometheus metric definitions."""

    def test_metrics_enabled_false_by_default(self):
        from dbwarden.metrics import metrics_enabled

        assert metrics_enabled() is False

    def test_metrics_enabled_true_with_env_var(self, monkeypatch):
        monkeypatch.setenv("DBWARDEN_METRICS", "true")
        from dbwarden.metrics import metrics_enabled

        assert metrics_enabled() is True

    def test_generate_metrics_contains_all_metric_families(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics

    def test_metrics_enabled_accepts_1_and_yes(self, monkeypatch):
        from dbwarden.metrics import metrics_enabled

        for val in ("1", "yes", "TRUE", "YES"):
            monkeypatch.setenv("DBWARDEN_METRICS", val)
            assert metrics_enabled() is True

    def test_generate_metrics_contains_all_metric_families(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics

        output = generate_metrics()
        assert "# HELP" in output
        for name in (
            "dbwarden_migrations_total",
            "dbwarden_migration_duration_seconds",
            "dbwarden_schema_version",
            "dbwarden_seed_version",
            "dbwarden_migrations_pending",
            "dbwarden_migration_errors_total",
        ):
            assert name in output

    def test_increment_and_generate(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, increment_migrations_total

        label = "test_inc_gen"
        increment_migrations_total(label, "0001", success=True)
        output = generate_metrics()
        assert f'database="{label}"' in output
        assert 'version="0001"' in output

    def test_observe_migration_duration(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, observe_migration_duration

        label = "test_obs_dur"
        observe_migration_duration(label, "0001", 1.5)
        output = generate_metrics()
        assert f'database="{label}"' in output
        assert "_bucket" in output

    def test_set_schema_version(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, set_schema_version

        label = "test_schema_ver"
        set_schema_version(label, "0003")
        output = generate_metrics()
        assert "dbwarden_schema_version" in output
        assert f'database="{label}"' in output

    def test_set_seed_version(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, set_seed_version

        label = "test_seed_ver"
        set_seed_version(label, "V0002")
        output = generate_metrics()
        assert "dbwarden_seed_version" in output
        assert f'database="{label}"' in output

    def test_set_pending_migrations(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, set_pending_migrations

        label = "test_pending_mig"
        set_pending_migrations(label, 5)
        output = generate_metrics()
        assert "dbwarden_migrations_pending" in output
        assert f'database="{label}"' in output

    def test_increment_migration_errors(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import generate_metrics, increment_migration_errors

        label = "test_err_inc"
        increment_migration_errors(label)
        output = generate_metrics()
        assert "dbwarden_migration_errors_total" in output
        assert f'database="{label}"' in output


class TestMetricsFallback:
    """Tests that metrics module works safely without prometheus_client."""

    def test_noop_functions_dont_raise(self):
        from dbwarden import metrics

        metrics.increment_migrations_total("x", "y")
        metrics.observe_migration_duration("x", "y", 1.0)
        metrics.set_schema_version("x", "1")
        metrics.set_seed_version("x", "1")
        metrics.set_pending_migrations("x", 1)
        metrics.increment_migration_errors("x")


class TestParseVersion:
    """Tests for the internal _parse_version helper."""

    def test_plain_number(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("0001") == 1.0

    def test_v_prefix(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("V0002") == 2.0

    def test_with_description(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("0003_add_users") == 3.0

    def test_v_prefix_with_description(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("V0001__seed_data") == 1.0

    def test_no_digits_returns_zero(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("abc") == 0.0

    def test_empty_string_returns_zero(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("") == 0.0

    def test_handles_long_versions(self):
        from dbwarden.metrics import _parse_version

        assert _parse_version("20240101120000") == 20240101120000.0


class TestMetricsRouter:
    """Tests for the FastAPI MetricsRouter endpoint."""

    def test_metrics_disabled_by_default(self):
        fastapi = pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import MetricsRouter

        app = FastAPI()
        app.include_router(MetricsRouter())
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "Metrics disabled" in response.text

    def test_metrics_enabled_returns_prometheus_format(self, monkeypatch):
        monkeypatch.setenv("DBWARDEN_METRICS", "true")

        fastapi = pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import MetricsRouter

        app = FastAPI()
        app.include_router(MetricsRouter())
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "# HELP" in response.text

    def test_metrics_content_type(self, monkeypatch):
        monkeypatch.setenv("DBWARDEN_METRICS", "true")

        fastapi = pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import MetricsRouter

        app = FastAPI()
        app.include_router(MetricsRouter())
        client = TestClient(app)

        response = client.get("/metrics")
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_router_mounted_on_prefix(self, monkeypatch):
        monkeypatch.setenv("DBWARDEN_METRICS", "true")

        fastapi = pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import MetricsRouter

        app = FastAPI()
        app.include_router(MetricsRouter(), prefix="/dbwarden")
        client = TestClient(app)

        response = client.get("/dbwarden/metrics")
        assert response.status_code == 200
        assert "# HELP" in response.text


class TestMetricsEdgeCases:
    """Edge cases for metrics."""

    def test_concurrent_metric_access(self):
        pytest.importorskip("prometheus_client")
        import threading

        from dbwarden.metrics import generate_metrics, increment_migrations_total, observe_migration_duration

        results = []

        def worker(idx):
            for i in range(10):
                increment_migrations_total(f"conc_db_{idx}", f"V{i:04d}")
                observe_migration_duration(f"conc_db_{idx}", f"V{i:04d}", float(i))
            results.append("done")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == "done" for r in results)
        output = generate_metrics()
        for i in range(4):
            assert f'database="conc_db_{i}"' in output

    def test_metrics_round_trip_values(self):
        pytest.importorskip("prometheus_client")
        from dbwarden.metrics import (
            generate_metrics,
            increment_migrations_total,
            set_pending_migrations,
        )

        set_pending_migrations("rt_test_db", 3)
        increment_migrations_total("rt_test_db", "0001")
        increment_migrations_total("rt_test_db", "0001")
        increment_migrations_total("rt_test_db", "0002")

        output = generate_metrics()

        match = re.search(
            r'^dbwarden_migrations_total\{database="rt_test_db",success="True",version="0001"\} (\d+\.?\d*)',
            output,
            re.MULTILINE,
        )
        assert match is not None
        assert float(match.group(1)) == 2.0

        match = re.search(
            r'^dbwarden_migrations_pending\{database="rt_test_db"\} (\d+\.?\d*)',
            output,
            re.MULTILINE,
        )
        assert match is not None
        assert float(match.group(1)) == 3.0

    def test_metrics_disabled_no_prometheus_output(self):
        fastapi = pytest.importorskip("fastapi")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from dbwarden.extensions.fastapi import MetricsRouter

        app = FastAPI()
        app.include_router(MetricsRouter())
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.text.strip().startswith("# Metrics disabled")
