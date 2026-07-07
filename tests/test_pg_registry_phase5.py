"""Golden tests and contract tests for Phase 5 handlers: StorageParams, Policies, Grants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry import (
    GrantsHandler,
    PoliciesHandler,
    RegistryDriver,
    StorageParamsHandler,
)
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
    _assemble_migration,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeTable:
    name: str = "users"
    pg_table: dict[str, Any] = field(default_factory=dict)
    pg_policies: list[dict[str, Any]] | None = None
    pg_grants: list[dict[str, Any]] | None = None
    columns: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Inline reference: StorageParams
# ---------------------------------------------------------------------------


def _inline_storage_params_diff(
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    model_by_name = {t.name: t for t in model_tables}
    all_tables = sorted(set(model_by_name.keys()) | {t for t in snapshot.get("tables", {})})

    for tname in all_tables:
        table = model_by_name.get(tname)
        if table is None:
            continue

        snap_entry: dict[str, Any] = {}
        snap_table = snapshot.get("tables", {}).get(tname, {})
        snap_pg = snap_table.get("pg_table") or snap_table.get("backend_table_spec") or {}
        snap_params = snap_pg.get("pg_storage_params", {}) or {}
        for k, v in snap_params.items():
            snap_entry[k] = v

        model_entry: dict[str, Any] = {}
        model_params = table.pg_table.get("pg_storage_params", {}) or {}
        for k, v in model_params.items():
            model_entry[k] = v

        all_keys = set(snap_entry.keys()) | set(model_entry.keys())
        for key in sorted(all_keys):
            snap_val = snap_entry.get(key)
            model_val = model_entry.get(key)
            if snap_val != model_val:
                upgrade_ops.append({
                    "type": "alter_pg_storage_param",
                    "table": tname,
                    "param": key,
                    "to_value": model_val,
                    "from_value": snap_val,
                })
                rollback_ops.append({
                    "type": "alter_pg_storage_param",
                    "table": tname,
                    "param": key,
                    "to_value": snap_val,
                    "from_value": model_val,
                })

    return upgrade_ops, rollback_ops


def _inline_storage_params_emit(
    ops: list[dict[str, Any]],
) -> list[MigrationStatement]:
    stmts: list[MigrationStatement] = []
    for op in ops:
        param = op["param"]
        to_val = op.get("to_value")
        from_val = op.get("from_value")
        if to_val is not None:
            up = f"ALTER TABLE {op['table']} SET ({param} = {to_val});"
        else:
            up = f"ALTER TABLE {op['table']} RESET ({param});"
        if from_val is not None:
            rb = f"ALTER TABLE {op['table']} SET ({param} = {from_val});"
        else:
            rb = f"ALTER TABLE {op['table']} RESET ({param});"
        stmts.append(MigrationStatement(
            order=StatementOrder.ALTER_TABLE_OPTIONS,
            upgrade_sql=up, rollback_sql=rb,
        ))
    return stmts


# ---------------------------------------------------------------------------
# Inline reference: Policies (RLS + policies)
# ---------------------------------------------------------------------------


def _inline_policies_diff(
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from dbwarden.engine.model_discovery import _build_create_policy_sql, _qualified_name, _quote_pg

    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    model_by_name = {t.name: t for t in model_tables}
    all_tables = sorted(set(model_by_name.keys()) | {t for t in snapshot.get("tables", {})})

    for tname in all_tables:
        table = model_by_name.get(tname)
        snap_table_meta = snapshot.get("tables", {}).get(tname, {})
        snap_pg_table = snap_table_meta.get("pg_table") or snap_table_meta.get("backend_table_spec") or {}
        snap_rls = bool(snap_pg_table.get("pg_rls", False))
        model_rls = bool(table.pg_table.get("pg_rls", False)) if table else False

        if snap_rls != model_rls:
            upgrade_ops.append({"type": "alter_pg_rls", "table": tname, "enable": model_rls})
            rollback_ops.append({"type": "alter_pg_rls", "table": tname, "enable": snap_rls})

        snap_policies_raw = snap_table_meta.get("pg_policies", []) or []
        snap_policies = {p["name"]: p for p in snap_policies_raw}
        model_policies_raw = (table.pg_policies or []) if table else []
        model_policies = {p["name"]: p for p in model_policies_raw}

        all_names = set(snap_policies.keys()) | set(model_policies.keys())
        for name in sorted(all_names):
            snap_pol = snap_policies.get(name)
            model_pol = model_policies.get(name)
            if snap_pol and not model_pol:
                upgrade_ops.append({"type": "drop_policy", "table": tname, "name": name, **snap_pol})
                rollback_ops.append({"type": "add_policy", "table": tname, "name": name, **snap_pol})
            elif model_pol and not snap_pol:
                upgrade_ops.append({"type": "add_policy", "table": tname, "name": name, **model_pol})
                rollback_ops.append({"type": "drop_policy", "table": tname, "name": name, **model_pol})
            elif model_pol != snap_pol:
                cmd_changed = model_pol.get("command") != snap_pol.get("command")
                permissive_changed = model_pol.get("permissive") != snap_pol.get("permissive")
                if cmd_changed or permissive_changed:
                    upgrade_ops.append({"type": "add_policy", "table": tname, "name": name, **model_pol})
                    upgrade_ops.append({"type": "drop_policy", "table": tname, "name": name, **snap_pol})
                    rollback_ops.append({"type": "add_policy", "table": tname, "name": name, **snap_pol})
                    rollback_ops.append({"type": "drop_policy", "table": tname, "name": name, **model_pol})
                else:
                    upgrade_ops.append({"type": "alter_policy", "table": tname, "name": name, **model_pol})
                    rollback_ops.append({"type": "alter_policy", "table": tname, "name": name, **snap_pol})

    return upgrade_ops, rollback_ops


def _inline_policies_emit(
    ops: list[dict[str, Any]],
) -> list[MigrationStatement]:
    from dbwarden.engine.model_discovery import (
        _build_alter_policy_sql,
        _build_create_policy_sql,
        _qualified_name,
        _quote_pg,
    )

    stmts: list[MigrationStatement] = []
    for op in ops:
        qname = _qualified_name(op.get("table", ""), op.get("schema"))
        if op["type"] == "alter_pg_rls":
            enable = op.get("enable", False)
            if enable:
                up = f"ALTER TABLE {qname} ENABLE ROW LEVEL SECURITY;"
                rb = f"ALTER TABLE {qname} DISABLE ROW LEVEL SECURITY;"
            else:
                up = f"ALTER TABLE {qname} DISABLE ROW LEVEL SECURITY;"
                rb = f"ALTER TABLE {qname} ENABLE ROW LEVEL SECURITY;"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_RLS,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op["type"] == "add_policy":
            up = _build_create_policy_sql(op, qname)
            rb = f"DROP POLICY IF EXISTS {_quote_pg(op['name'])} ON {qname};"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op["type"] == "drop_policy":
            name = op["name"]
            up = f"DROP POLICY IF EXISTS {_quote_pg(name)} ON {qname};"
            rb = f"-- Cannot auto-restore policy {name}; recreate from snapshot"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op["type"] == "alter_policy":
            up = _build_alter_policy_sql(op, qname)
            name = op["name"]
            rb = f"-- Cannot auto-restore altered policy {name}; recreate from snapshot"
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_POLICY,
                upgrade_sql=up, rollback_sql=rb,
            ))
    return stmts


# ---------------------------------------------------------------------------
# Inline reference: Grants
# ---------------------------------------------------------------------------


def _inline_grants_diff(
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    upgrade_ops: list[dict[str, Any]] = []
    rollback_ops: list[dict[str, Any]] = []

    model_by_name = {t.name: t for t in model_tables}
    all_tables = sorted(set(model_by_name.keys()) | {t for t in snapshot.get("tables", {})})

    for tname in all_tables:
        table = model_by_name.get(tname)
        snap_grants_raw = snapshot.get("tables", {}).get(tname, {}).get("pg_grants", []) or []
        snap_grants = {_grant_key(g): g for g in snap_grants_raw}
        model_grants_raw = (table.pg_grants or []) if table else []
        model_grants = {_grant_key(g): g for g in model_grants_raw}

        for key, grant in model_grants.items():
            if key not in snap_grants:
                upgrade_ops.append({"type": "add_grant", "table": tname, **grant})
                rollback_ops.append({"type": "revoke_grant", "table": tname, **grant})

        for key, grant in snap_grants.items():
            if key not in model_grants:
                upgrade_ops.append({"type": "revoke_grant", "table": tname, **grant})
                rollback_ops.append({"type": "add_grant", "table": tname, **grant})

    return upgrade_ops, rollback_ops


def _inline_grants_emit(
    ops: list[dict[str, Any]],
) -> list[MigrationStatement]:
    from dbwarden.engine.model_discovery import _build_grant_sql, _build_revoke_sql, _qualified_name

    stmts: list[MigrationStatement] = []
    for op in ops:
        qname = _qualified_name(op["table"], op.get("schema"))
        if op["type"] == "add_grant":
            up = _build_grant_sql(op, qname)
            rb = _build_revoke_sql(op, qname)
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_GRANT,
                upgrade_sql=up, rollback_sql=rb,
            ))
        elif op["type"] == "revoke_grant":
            up = _build_revoke_sql(op, qname)
            rb = _build_grant_sql(op, qname)
            stmts.append(MigrationStatement(
                order=StatementOrder.ALTER_PG_GRANT,
                upgrade_sql=up, rollback_sql=rb,
            ))
    return stmts


def _grant_key(g: dict) -> tuple:
    privs: tuple[str, ...]
    raw = g.get("privileges", ["ALL"])
    if isinstance(raw, list):
        privs = tuple(sorted(raw))
    else:
        privs = (raw,)
    return (g.get("role", "PUBLIC"), privs, bool(g.get("grantable", False)))


# ---------------------------------------------------------------------------
# Handler-driven diff+emit helper
# ---------------------------------------------------------------------------


def _handler_diff_sql(
    handler_cls: Any,
    snapshot: dict[str, Any],
    model_tables: list[FakeTable],
) -> tuple[str, str]:
    handler = handler_cls()
    snap_spec = handler.canonicalize(handler.extract(snapshot))
    model_spec = handler.canonicalize(handler.model_spec_from_tables(model_tables))
    up_ops, rb_ops = handler.diff(snap_spec, model_spec)
    up_stmts = sum((handler.emit(op) for op in up_ops), [])
    rb_stmts = sum((handler.emit(op) for op in rb_ops), [])
    up_sql, rb_sql = _assemble_migration(up_stmts + rb_stmts)
    return up_sql, rb_sql


# ---------------------------------------------------------------------------
# Test data: StorageParams
# ---------------------------------------------------------------------------

EMPTY_SNAPSHOT: dict[str, Any] = {"tables": {}}

SNAPSHOT_STORAGE = {
    "tables": {
        "users": {
            "pg_table": {
                "pg_storage_params": {
                    "fillfactor": 90,
                },
            },
        },
        "orders": {
            "pg_table": {
                "pg_storage_params": {
                    "autovacuum_enabled": "off",
                    "fillfactor": 100,
                },
            },
        },
    },
}

# model has one param added, one param changed, one param removed
MODEL_STORAGE_CHANGED = [
    FakeTable(
        name="users",
        pg_table={
            "pg_storage_params": {
                "fillfactor": 95,
                "toast_tuple_target": 128,
            },
        },
    ),
    FakeTable(
        name="orders",
        pg_table={
            "pg_storage_params": {
                "fillfactor": 100,
            },
        },
    ),
]

MODEL_STORAGE_NO_STORAGE = [
    FakeTable(name="users", pg_table={}),
    FakeTable(name="orders", pg_table={}),
]

MODEL_STORAGE_NEW_TABLE = [
    FakeTable(
        name="users",
        pg_table={
            "pg_storage_params": {
                "fillfactor": 90,
            },
        },
    ),
    FakeTable(
        name="audit_log",
        pg_table={
            "pg_storage_params": {
                "fillfactor": 75,
            },
        },
    ),
]

# ---------------------------------------------------------------------------
# Test data: Policies
# ---------------------------------------------------------------------------

SNAPSHOT_POLICIES = {
    "tables": {
        "users": {
            "pg_table": {"pg_rls": True},
            "pg_policies": [
                {"name": "user_sel", "command": "SELECT", "role": "PUBLIC",
                 "using": "active = true"},
            ],
        },
        "orders": {
            "pg_table": {"pg_rls": False},
            "pg_policies": [
                {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
                 "using": "amount > 0"},
            ],
        },
    },
}

SNAPSHOT_NO_RLS: dict[str, Any] = {
    "tables": {
        "users": {
            "pg_table": {},
            "pg_policies": [],
        },
    },
}

MODEL_POLICIES_UNCHANGED = [
    FakeTable(
        name="users",
        pg_table={"pg_rls": True},
        pg_policies=[
            {"name": "user_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "active = true"},
        ],
    ),
    FakeTable(
        name="orders",
        pg_table={"pg_rls": False},
        pg_policies=[
            {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "amount > 0"},
        ],
    ),
]

MODEL_POLICIES_ADD_RLS_AND_POLICY = [
    FakeTable(
        name="users",
        pg_table={"pg_rls": True},
        pg_policies=[
            {"name": "user_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "active = true"},
            {"name": "user_ins", "command": "INSERT", "role": "admin",
             "with_check": "email IS NOT NULL"},
        ],
    ),
    FakeTable(
        name="orders",
        pg_table={"pg_rls": True},
        pg_policies=[
            {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "amount > 0"},
        ],
    ),
]

MODEL_POLICIES_ALTER_CMD = [
    FakeTable(
        name="users",
        pg_table={"pg_rls": True},
        pg_policies=[
            {"name": "user_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "active = true AND deleted = false"},
        ],
    ),
    FakeTable(
        name="orders",
        pg_table={"pg_rls": False},
        pg_policies=[
            {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "amount > 0"},
        ],
    ),
]

MODEL_POLICIES_ALTER_ROLE = [
    FakeTable(
        name="users",
        pg_table={"pg_rls": True},
        pg_policies=[
            {"name": "user_sel", "command": "SELECT", "role": "app_user",
             "using": "active = true"},
        ],
    ),
    FakeTable(
        name="orders",
        pg_table={"pg_rls": False},
        pg_policies=[
            {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "amount > 0"},
        ],
    ),
]

MODEL_POLICIES_DROP_RLS_DROP_POLICY = [
    FakeTable(
        name="users",
        pg_table={"pg_rls": False},
        pg_policies=[],
    ),
    FakeTable(
        name="orders",
        pg_table={"pg_rls": False},
        pg_policies=[
            {"name": "order_sel", "command": "SELECT", "role": "PUBLIC",
             "using": "amount > 0"},
        ],
    ),
]

# ---------------------------------------------------------------------------
# Test data: Grants
# ---------------------------------------------------------------------------

SNAPSHOT_GRANTS = {
    "tables": {
        "users": {
            "pg_grants": [
                {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
                {"role": "app_admin", "privileges": ["INSERT", "UPDATE"], "grantable": True},
            ],
        },
        "orders": {
            "pg_grants": [
                {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
            ],
        },
    },
}

MODEL_GRANTS_ADD_REVOKE = [
    FakeTable(
        name="users",
        pg_grants=[
            {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
            {"role": "app_admin", "privileges": ["INSERT", "UPDATE", "DELETE"], "grantable": True},
        ],
    ),
    FakeTable(
        name="orders",
        pg_grants=[
            {"role": "app_reader", "privileges": ["SELECT"], "grantable": False},
        ],
    ),
]

MODEL_GRANTS_UNCHANGED = [
    FakeTable(
        name="users",
        pg_grants=[
            {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
            {"role": "app_admin", "privileges": ["INSERT", "UPDATE"], "grantable": True},
        ],
    ),
    FakeTable(
        name="orders",
        pg_grants=[
            {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
        ],
    ),
]

MODEL_GRANTS_NEW_TABLE = [
    FakeTable(
        name="users",
        pg_grants=[
            {"role": "PUBLIC", "privileges": ["SELECT"], "grantable": False},
        ],
    ),
    FakeTable(
        name="audit_log",
        pg_grants=[
            {"role": "PUBLIC", "privileges": ["ALL"], "grantable": False},
        ],
    ),
]


# ===================================================================
# Golden byte-equivalence tests: StorageParamsHandler
# ===================================================================

class TestStorageParamsHandlerGolden:
    HANDLER_CLS = StorageParamsHandler

    @pytest.mark.parametrize(
        "snapshot,model_tables,label",
        [
            (EMPTY_SNAPSHOT, [], "empty"),
            (SNAPSHOT_STORAGE, MODEL_STORAGE_CHANGED, "add_change_remove"),
            (SNAPSHOT_STORAGE, MODEL_STORAGE_NO_STORAGE, "remove_all"),
            (EMPTY_SNAPSHOT, MODEL_STORAGE_NEW_TABLE, "new_table"),
            (SNAPSHOT_STORAGE, [
                FakeTable(name="users", pg_table={"pg_storage_params": {"fillfactor": 90}}),
                FakeTable(name="orders", pg_table={"pg_storage_params": {"autovacuum_enabled": "off", "fillfactor": 100}}),
            ], "unchanged"),
        ],
    )
    def test_sql_byte_equivalence(
        self,
        snapshot: dict[str, Any],
        model_tables: list[FakeTable],
        label: str,
    ) -> None:
        inline_up_ops, inline_rb_ops = _inline_storage_params_diff(snapshot, model_tables)
        inline_stmts = _inline_storage_params_emit(inline_up_ops) + _inline_storage_params_emit(inline_rb_ops)
        inline_up_sql, inline_rb_sql = _assemble_migration(inline_stmts)

        handler_up_sql, handler_rb_sql = _handler_diff_sql(
            self.HANDLER_CLS, snapshot, model_tables
        )

        assert handler_up_sql == inline_up_sql, (
            f"Upgrade SQL mismatch for {label}\n"
            f"  inline:  {inline_up_sql!r}\n"
            f"  handler: {handler_up_sql!r}"
        )
        assert handler_rb_sql == inline_rb_sql, (
            f"Rollback SQL mismatch for {label}\n"
            f"  inline:  {inline_rb_sql!r}\n"
            f"  handler: {handler_rb_sql!r}"
        )


# ===================================================================
# Golden byte-equivalence tests: PoliciesHandler
# ===================================================================

class TestPoliciesHandlerGolden:
    HANDLER_CLS = PoliciesHandler

    @pytest.mark.parametrize(
        "snapshot,model_tables,label",
        [
            (EMPTY_SNAPSHOT, [], "empty"),
            (SNAPSHOT_POLICIES, MODEL_POLICIES_UNCHANGED, "unchanged"),
            (SNAPSHOT_POLICIES, MODEL_POLICIES_ADD_RLS_AND_POLICY, "add_rls_and_policy"),
            (SNAPSHOT_POLICIES, MODEL_POLICIES_ALTER_CMD, "alter_using"),
            (SNAPSHOT_POLICIES, MODEL_POLICIES_ALTER_ROLE, "alter_role"),
            (SNAPSHOT_POLICIES, MODEL_POLICIES_DROP_RLS_DROP_POLICY, "drop_rls_and_policy"),
            (SNAPSHOT_NO_RLS, MODEL_POLICIES_ADD_RLS_AND_POLICY, "from_no_rls"),
        ],
    )
    def test_sql_byte_equivalence(
        self,
        snapshot: dict[str, Any],
        model_tables: list[FakeTable],
        label: str,
    ) -> None:
        inline_up_ops, inline_rb_ops = _inline_policies_diff(snapshot, model_tables)
        inline_stmts = _inline_policies_emit(inline_up_ops) + _inline_policies_emit(inline_rb_ops)
        inline_up_sql, inline_rb_sql = _assemble_migration(inline_stmts)

        handler_up_sql, handler_rb_sql = _handler_diff_sql(
            self.HANDLER_CLS, snapshot, model_tables
        )

        assert handler_up_sql == inline_up_sql, (
            f"Upgrade SQL mismatch for {label}\n"
            f"  inline:  {inline_up_sql!r}\n"
            f"  handler: {handler_up_sql!r}"
        )
        assert handler_rb_sql == inline_rb_sql, (
            f"Rollback SQL mismatch for {label}\n"
            f"  inline:  {inline_rb_sql!r}\n"
            f"  handler: {handler_rb_sql!r}"
        )


# ===================================================================
# Golden byte-equivalence tests: GrantsHandler
# ===================================================================

class TestGrantsHandlerGolden:
    HANDLER_CLS = GrantsHandler

    @pytest.mark.parametrize(
        "snapshot,model_tables,label",
        [
            (EMPTY_SNAPSHOT, [], "empty"),
            (SNAPSHOT_GRANTS, MODEL_GRANTS_UNCHANGED, "unchanged"),
            (SNAPSHOT_GRANTS, MODEL_GRANTS_ADD_REVOKE, "add_and_revoke"),
            (EMPTY_SNAPSHOT, MODEL_GRANTS_NEW_TABLE, "new_table_with_grants"),
            (SNAPSHOT_GRANTS, [], "remove_all"),
        ],
    )
    def test_sql_byte_equivalence(
        self,
        snapshot: dict[str, Any],
        model_tables: list[FakeTable],
        label: str,
    ) -> None:
        inline_up_ops, inline_rb_ops = _inline_grants_diff(snapshot, model_tables)
        inline_stmts = _inline_grants_emit(inline_up_ops) + _inline_grants_emit(inline_rb_ops)
        inline_up_sql, inline_rb_sql = _assemble_migration(inline_stmts)

        handler_up_sql, handler_rb_sql = _handler_diff_sql(
            self.HANDLER_CLS, snapshot, model_tables
        )

        assert handler_up_sql == inline_up_sql, (
            f"Upgrade SQL mismatch for {label}\n"
            f"  inline:  {inline_up_sql!r}\n"
            f"  handler: {handler_up_sql!r}"
        )
        assert handler_rb_sql == inline_rb_sql, (
            f"Rollback SQL mismatch for {label}\n"
            f"  inline:  {inline_rb_sql!r}\n"
            f"  handler: {handler_rb_sql!r}"
        )


# ===================================================================
# Contract tests: StorageParamsHandler
# ===================================================================

class TestStorageParamsHandlerContract:
    HANDLER = StorageParamsHandler()

    def test_canonical_idempotent(self) -> None:
        spec = {"users": {"fillfactor": 90}}
        c1 = self.HANDLER.canonicalize(spec)
        c2 = self.HANDLER.canonicalize(c1)
        assert c1 == c2

    def test_canonical_empty(self) -> None:
        assert self.HANDLER.canonicalize({}) == {}
        assert self.HANDLER.canonicalize(None) == {}

    def test_unchanged_produces_empty_diff(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_STORAGE))
        model = self.HANDLER.canonicalize(self.HANDLER.model_spec_from_tables([
            FakeTable(name="users", pg_table={"pg_storage_params": {"fillfactor": 90}}),
            FakeTable(name="orders", pg_table={"pg_storage_params": {"autovacuum_enabled": "off", "fillfactor": 100}}),
        ]))
        up, rb = self.HANDLER.diff(snap, model)
        assert up == []
        assert rb == []

    def test_add_param(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_STORAGE))
        model = self.HANDLER.canonicalize(self.HANDLER.model_spec_from_tables([
            FakeTable(name="users", pg_table={"pg_storage_params": {"fillfactor": 90, "toast_tuple_target": 128}}),
            FakeTable(name="orders", pg_table={"pg_storage_params": {"autovacuum_enabled": "off", "fillfactor": 100}}),
        ]))
        up, rb = self.HANDLER.diff(snap, model)
        assert len(up) == 1
        assert up[0].object_type == "alter_pg_storage_param"
        assert up[0].upgrade_attrs["param"] == "toast_tuple_target"
        assert up[0].upgrade_attrs["to_value"] == 128

    def test_drop_param(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_STORAGE))
        model = self.HANDLER.canonicalize(self.HANDLER.model_spec_from_tables([
            FakeTable(name="users", pg_table={"pg_storage_params": {}}),
            FakeTable(name="orders", pg_table={"pg_storage_params": {"autovacuum_enabled": "off", "fillfactor": 100}}),
        ]))
        up, _ = self.HANDLER.diff(snap, model)
        assert len(up) == 1
        up_keys = {op.upgrade_attrs["param"] for op in up}
        assert "fillfactor" in up_keys

    def test_emit_reset_when_value_none(self) -> None:
        from dbwarden.engine.pg_registry.protocol import Op
        op = Op(
            object_type="alter_pg_storage_param",
            upgrade_attrs={"table": "users", "param": "fillfactor", "to_value": None},
            rollback_attrs={},
        )
        stmts = self.HANDLER.emit(op)
        assert "RESET" in stmts[0].upgrade_sql


# ===================================================================
# Contract tests: PoliciesHandler
# ===================================================================

class TestPoliciesHandlerContract:
    HANDLER = PoliciesHandler()

    def test_canonical_idempotent(self) -> None:
        spec = {"users": {"rls": True, "policies": {"p1": {"name": "p1"}}}}
        c1 = self.HANDLER.canonicalize(spec)
        c2 = self.HANDLER.canonicalize(c1)
        assert c1 == c2

    def test_canonical_empty(self) -> None:
        assert self.HANDLER.canonicalize({}) == {}
        assert self.HANDLER.canonicalize(None) == {}

    def test_unchanged_produces_empty_diff(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_POLICIES))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_POLICIES_UNCHANGED)
        )
        up, rb = self.HANDLER.diff(snap, model)
        assert up == []
        assert rb == []

    def test_alter_pg_rls_on_add(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_POLICIES))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_POLICIES_ADD_RLS_AND_POLICY)
        )
        up, _ = self.HANDLER.diff(snap, model)
        rls_ops = [op for op in up if op.object_type == "alter_pg_rls"]
        assert len(rls_ops) == 1
        assert rls_ops[0].upgrade_attrs["enable"] is True
        assert rls_ops[0].upgrade_attrs["table"] == "orders"

    def test_add_policy_op(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_POLICIES))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_POLICIES_ADD_RLS_AND_POLICY)
        )
        up, _ = self.HANDLER.diff(snap, model)
        add_ops = [op for op in up if op.object_type == "add_policy"]
        assert len(add_ops) == 1
        assert add_ops[0].upgrade_attrs["name"] == "user_ins"

    def test_drop_policy_op(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_POLICIES))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_POLICIES_DROP_RLS_DROP_POLICY)
        )
        up, _ = self.HANDLER.diff(snap, model)
        drop_ops = [op for op in up if op.object_type == "drop_policy"]
        assert len(drop_ops) == 1
        assert drop_ops[0].upgrade_attrs["name"] == "user_sel"

    def test_alter_policy_on_role_change(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_POLICIES))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_POLICIES_ALTER_ROLE)
        )
        up, _ = self.HANDLER.diff(snap, model)
        alter_ops = [op for op in up if op.object_type == "alter_policy"]
        assert len(alter_ops) == 1
        assert alter_ops[0].upgrade_attrs["name"] == "user_sel"
        assert alter_ops[0].upgrade_attrs["role"] == "app_user"


# ===================================================================
# Contract tests: GrantsHandler
# ===================================================================

class TestGrantsHandlerContract:
    HANDLER = GrantsHandler()

    def test_canonical_idempotent(self) -> None:
        g = {"role": "PUBLIC", "privileges": ["SELECT"]}
        spec = {"users": {_grant_key(g): g}}
        c1 = self.HANDLER.canonicalize(spec)
        c2 = self.HANDLER.canonicalize(c1)
        assert c1 == c2

    def test_canonical_empty(self) -> None:
        assert self.HANDLER.canonicalize({}) == {}
        assert self.HANDLER.canonicalize(None) == {}

    def test_unchanged_produces_empty_diff(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_GRANTS))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_GRANTS_UNCHANGED)
        )
        up, rb = self.HANDLER.diff(snap, model)
        assert up == []
        assert rb == []

    def test_add_grant_op(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_GRANTS))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_GRANTS_ADD_REVOKE)
        )
        up, _ = self.HANDLER.diff(snap, model)
        add_ops = [op for op in up if op.object_type == "add_grant"]
        assert len(add_ops) == 2
        roles = {op.upgrade_attrs.get("role") for op in add_ops}
        assert "app_reader" in roles

    def test_revoke_grant_op(self) -> None:
        snap = self.HANDLER.canonicalize(self.HANDLER.extract(SNAPSHOT_GRANTS))
        model = self.HANDLER.canonicalize(
            self.HANDLER.model_spec_from_tables(MODEL_GRANTS_ADD_REVOKE)
        )
        up, _ = self.HANDLER.diff(snap, model)
        revoke_ops = [op for op in up if op.object_type == "revoke_grant"]
        assert len(revoke_ops) == 2
        revoked_roles = {op.upgrade_attrs.get("role") for op in revoke_ops}
        assert "PUBLIC" in revoked_roles  # orders had PUBLIC, model doesn't


# ===================================================================
# Churn tests: RLS-FORCE convergence
# ===================================================================


class TestRlsForceChurn:

    def test_rls_no_force_does_not_emit_no_force(self):
        """When RLS is enabled but FORCE was never set, no NO FORCE should be emitted."""
        snap_spec = {"users": {"rls": True}}
        model_spec = {"users": {"rls": True}}
        handler = PoliciesHandler()
        c_snap = handler.canonicalize(snap_spec)
        c_model = handler.canonicalize(model_spec)
        up, rb = handler.diff(c_snap, c_model)
        assert up == [], f"Expected 0 ops when force is absent on both sides, got {len(up)}"

    def test_rls_force_add_emits_force(self):
        """Adding RLS-FORCE to an existing table with RLS enabled emits FORCE."""
        snap_spec = {"users": {"rls": True}}
        model_spec = {"users": {"rls": True, "force": True}}
        handler = PoliciesHandler()
        c_snap = handler.canonicalize(snap_spec)
        c_model = handler.canonicalize(model_spec)
        up, rb = handler.diff(c_snap, c_model)
        force_ops = [op for op in up if op.object_type == "alter_pg_rls"]
        assert len(force_ops) == 1
        assert force_ops[0].upgrade_attrs.get("force") is True

    def test_rls_force_remove_emits_no_force(self):
        """Removing RLS-FORCE emits NO FORCE."""
        snap_spec = {"users": {"rls": True, "force": True}}
        model_spec = {"users": {"rls": True}}
        handler = PoliciesHandler()
        c_snap = handler.canonicalize(snap_spec)
        c_model = handler.canonicalize(model_spec)
        up, rb = handler.diff(c_snap, c_model)
        force_ops = [op for op in up if op.object_type == "alter_pg_rls"]
        assert len(force_ops) == 1
        up_force = force_ops[0].upgrade_attrs.get("force")
        assert up_force is None or up_force is False

    def test_rls_force_two_cycle_convergence(self):
        """Two-cycle convergence: canonicalize is idempotent for FORCE."""
        spec = {"users": {"rls": True, "force": True}}
        handler = PoliciesHandler()
        c1 = handler.canonicalize(spec)
        c2 = handler.canonicalize(c1)
        assert c1 == c2
        up, rb = handler.diff(c1, c2)
        assert up == []
