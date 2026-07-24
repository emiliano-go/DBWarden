"""SQL helpers object plugins need, re-exported as public API.

Object handlers that live outside core still have to quote identifiers the way
core does and, on ClickHouse, emit ``ON CLUSTER`` the way core does. Vendoring
copies would let plugin SQL drift from core's, so the shared implementations are
surfaced here (and through ``dbwarden.engine.core``) instead of leaving plugins
to reach into backend internals.
"""

from __future__ import annotations

from dbwarden.engine.backends.clickhouse.cluster import (
    ClusterableStatement,
    emit_with_cluster,
)
from dbwarden.engine.backends.clickhouse.secrets import (
    REDACTED,
    has_visible_secrets,
    strip_secret_values,
)
from dbwarden.engine.backends.postgresql.render import (
    _build_alter_policy_sql as build_alter_policy_sql,
    _build_create_policy_sql as build_create_policy_sql,
    _build_grant_sql as build_grant_sql,
    _build_revoke_sql as build_revoke_sql,
    _quote_pg as quote_pg,
)


def qualified_name(name: str, schema: str | None) -> str:
    """Return ``schema.name`` when a schema is set, otherwise ``name``."""
    if schema:
        return f"{schema}.{name}"
    return name


__all__ = [
    "ClusterableStatement",
    "REDACTED",
    "build_alter_policy_sql",
    "build_create_policy_sql",
    "build_grant_sql",
    "build_revoke_sql",
    "emit_with_cluster",
    "has_visible_secrets",
    "qualified_name",
    "quote_pg",
    "strip_secret_values",
]
