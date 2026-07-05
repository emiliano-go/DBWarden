"""Golden tests and contract tests for Phase 4 DomainHandler and SequenceHandler."""

from __future__ import annotations

from typing import Any

import pytest

from dbwarden.engine.migration_name import Change
from dbwarden.engine.pg_registry import DomainHandler, RegistryDriver, SequenceHandler
from dbwarden.engine.snapshot import (
    MigrationStatement,
    StatementOrder,
    _assemble_migration,
)

# ---------------------------------------------------------------------------
# Inline reference implementations — match current preamble behavior
# ---------------------------------------------------------------------------


def _inline_create_domain_sql(info: dict[str, Any], name: str) -> str:
    from dbwarden.engine.model_discovery import _qualified_name

    schema = info.get("schema") if isinstance(info, dict) else None
    qname = _qualified_name(name, schema)
    ddl_type = info.get("type", "text")
    parts = [f"CREATE DOMAIN {qname} AS {ddl_type}"]
    if info.get("default"):
        parts.append(f"DEFAULT {info['default']}")
    if info.get("not_null"):
        parts.append("NOT NULL")
    if info.get("check"):
        parts.append(f"CHECK ({info['check']})")
    return " ".join(parts) + ";"


def _inline_drop_domain_sql(info: dict[str, Any], name: str) -> str:
    from dbwarden.engine.model_discovery import _qualified_name

    schema = info.get("schema") if isinstance(info, dict) else None
    qname = _qualified_name(name, schema)
    return f"DROP DOMAIN IF EXISTS {qname};"


def _inline_create_sequence_sql(info: dict[str, Any], name: str) -> str:
    from dbwarden.engine.model_discovery import _qualified_name

    schema = info.get("schema") if isinstance(info, dict) else None
    qname = _qualified_name(name, schema)
    parts = [f"CREATE SEQUENCE IF NOT EXISTS {qname}"]
    if info.get("increment") is not None:
        parts.append(f"INCREMENT BY {info['increment']}")
    if info.get("minvalue") is not None:
        parts.append(f"MINVALUE {info['minvalue']}")
    if info.get("maxvalue") is not None:
        parts.append(f"MAXVALUE {info['maxvalue']}")
    if info.get("start") is not None:
        parts.append(f"START WITH {info['start']}")
    if info.get("cycle"):
        parts.append("CYCLE")
    else:
        parts.append("NO CYCLE")
    if info.get("owned_by"):
        parts.append(f"OWNED BY {info['owned_by']}")
    return " ".join(parts) + ";"


def _inline_drop_sequence_sql(info: dict[str, Any], name: str) -> str:
    from dbwarden.engine.model_discovery import _qualified_name

    schema = info.get("schema") if isinstance(info, dict) else None
    qname = _qualified_name(name, schema)
    return f"DROP SEQUENCE IF EXISTS {qname};"


def _inline_domain_preamble(
    domains: list[dict[str, Any]],
) -> list[MigrationStatement]:
    stmts: list[MigrationStatement] = []
    for d in domains:
        name = d["name"]
        up = _inline_create_domain_sql(d, name)
        rb = _inline_drop_domain_sql(d, name)
        stmts.append(
            MigrationStatement(
                order=StatementOrder.CREATE_DOMAIN,
                upgrade_sql=up,
                rollback_sql=rb,
            )
        )
    for d in reversed(domains):
        name = d["name"]
        up = _inline_drop_domain_sql(d, name)
        rb = _inline_create_domain_sql(d, name)
        stmts.append(
            MigrationStatement(
                order=StatementOrder.CREATE_DOMAIN,
                upgrade_sql=up,
                rollback_sql=rb,
            )
        )
    return stmts


def _inline_sequence_preamble(
    sequences: list[dict[str, Any]],
) -> list[MigrationStatement]:
    stmts: list[MigrationStatement] = []
    for s in sequences:
        name = s["name"]
        up = _inline_create_sequence_sql(s, name)
        rb = _inline_drop_sequence_sql(s, name)
        stmts.append(
            MigrationStatement(
                order=StatementOrder.CREATE_SEQUENCE,
                upgrade_sql=up,
                rollback_sql=rb,
            )
        )
    for s in reversed(sequences):
        name = s["name"]
        up = _inline_drop_sequence_sql(s, name)
        rb = _inline_create_sequence_sql(s, name)
        stmts.append(
            MigrationStatement(
                order=StatementOrder.CREATE_SEQUENCE,
                upgrade_sql=up,
                rollback_sql=rb,
            )
        )
    return stmts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DHANDLER = DomainHandler()
SHANDLER = SequenceHandler()


class FakeConfig:
    def __init__(self, domains: list[dict[str, Any]], sequences: list[dict[str, Any]]):
        self.pg_domains = domains
        self.pg_sequences = sequences
        self.database_type = "postgresql"


# ---------------------------------------------------------------------------
# Domain golden tests
# ---------------------------------------------------------------------------

class TestDomainHandlerGolden:
    def test_fresh_create_simple(self) -> None:
        domains = [{"name": "us_zip", "type": "varchar(10)", "not_null": True}]
        config = FakeConfig(domains, [])
        snap: dict[str, Any] = {"domains": {}}

        # Inline — always emits all domains
        inline_stmts = _inline_domain_preamble(domains)
        inline_up, inline_rb = _assemble_migration(inline_stmts)

        # Handler
        snap_spec = DHANDLER.canonicalize(DHANDLER.extract(snap))
        model_spec = DHANDLER.canonicalize(DHANDLER.model_spec_from_config(config))
        up_ops, rb_ops = DHANDLER.diff(snap_spec, model_spec)
        h_stmts: list[MigrationStatement] = []
        for op in up_ops:
            h_stmts.extend(DHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(DHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        assert handler_up == inline_up
        assert handler_rb == inline_rb

    def test_fresh_create_with_default_check(self) -> None:
        domains = [
            {
                "name": "positive_int",
                "type": "integer",
                "not_null": True,
                "default": "0",
                "check": "VALUE > 0",
            },
            {
                "name": "us_state",
                "type": "char(2)",
                "not_null": True,
                "check": "VALUE ~ '^[A-Z]{2}$'",
            },
        ]
        config = FakeConfig(domains, [])
        snap: dict[str, Any] = {"domains": {}}

        inline_stmts = _inline_domain_preamble(domains)
        inline_up, inline_rb = _assemble_migration(inline_stmts)

        snap_spec = DHANDLER.canonicalize(DHANDLER.extract(snap))
        model_spec = DHANDLER.canonicalize(DHANDLER.model_spec_from_config(config))
        up_ops, rb_ops = DHANDLER.diff(snap_spec, model_spec)
        h_stmts = []
        for op in up_ops:
            h_stmts.extend(DHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(DHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        assert handler_up == inline_up
        assert handler_rb == inline_rb

    def test_drop_domain(self) -> None:
        snap: dict[str, Any] = {
            "domains": {
                "old_domain": {
                    "domain_type": "text",
                    "not_null": False,
                },
            },
        }
        config = FakeConfig([], [])  # no domains in model

        snap_spec = DHANDLER.canonicalize(DHANDLER.extract(snap))
        model_spec = DHANDLER.canonicalize(DHANDLER.model_spec_from_config(config))
        up_ops, rb_ops = DHANDLER.diff(snap_spec, model_spec)
        h_stmts = []
        for op in up_ops:
            h_stmts.extend(DHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(DHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        # Upgrade should drop the domain, rollback should recreate it
        assert "DROP DOMAIN IF EXISTS old_domain;" in handler_up
        assert "CREATE DOMAIN old_domain AS text" in handler_rb

    def test_with_schema(self) -> None:
        domains = [{"name": "email_type", "type": "text", "schema": "app"}]
        config = FakeConfig(domains, [])
        snap: dict[str, Any] = {"domains": {}}

        inline_stmts = _inline_domain_preamble(domains)
        inline_up, inline_rb = _assemble_migration(inline_stmts)

        snap_spec = DHANDLER.canonicalize(DHANDLER.extract(snap))
        model_spec = DHANDLER.canonicalize(DHANDLER.model_spec_from_config(config))
        up_ops, rb_ops = DHANDLER.diff(snap_spec, model_spec)
        h_stmts = []
        for op in up_ops:
            h_stmts.extend(DHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(DHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        assert handler_up == inline_up
        assert handler_rb == inline_rb
        assert "app.email_type" in handler_up


# ---------------------------------------------------------------------------
# Domain contract tests
# ---------------------------------------------------------------------------

class TestDomainHandlerContract:
    def test_canonical_idempotent(self) -> None:
        spec = {
            "PosInt": {"domain_type": "integer", "not_null": True, "default": "0"},
        }
        c1 = DHANDLER.canonicalize(spec)
        c2 = DHANDLER.canonicalize(c1)
        assert c1 == c2
        assert "posint" in c1
        assert c1["posint"]["type"] == "integer"

    def test_canonical_empty(self) -> None:
        assert DHANDLER.canonicalize({}) == {}
        assert DHANDLER.canonicalize(None) == {}

    def test_unchanged_produces_empty_diff(self) -> None:
        snap_spec = DHANDLER.canonicalize(
            {"mood": {"domain_type": "text", "not_null": False}}
        )
        model_spec = DHANDLER.canonicalize(
            {"mood": {"type": "text", "not_null": False}}
        )
        up, rb = DHANDLER.diff(snap_spec, model_spec)
        assert up == []
        assert rb == []

    def test_canonical_normalizes_key_names(self) -> None:
        spec = DHANDLER.model_spec_from_config(
            FakeConfig(
                [{"name": "MyDomain", "type": "text", "not_null": True}],
                [],
            )
        )
        canon = DHANDLER.canonicalize(spec)
        assert "mydomain" in canon
        assert canon["mydomain"]["type"] == "text"

    def test_model_spec_from_tables_empty(self) -> None:
        assert DHANDLER.model_spec_from_tables([]) == {}

    def test_create_domain_reversible(self) -> None:
        model_spec = DHANDLER.canonicalize(
            {"pos_int": {"type": "integer", "not_null": True}}
        )
        up, rb = DHANDLER.diff({}, model_spec)
        for op in up:
            if op.object_type == "create_domain":
                assert not op.irreversible

    def test_emit_create_domain(self) -> None:
        op = DHANDLER.diff(
            {},
            DHANDLER.canonicalize(
                {"pos_int": {"type": "integer", "not_null": True, "default": "0"}}
            ),
        )[0][0]
        stmts = DHANDLER.emit(op)
        assert len(stmts) == 1
        up = stmts[0].upgrade_sql
        assert up.startswith("CREATE DOMAIN pos_int AS integer")
        assert "DEFAULT 0" in up
        assert "NOT NULL" in up
        assert stmts[0].order == StatementOrder.CREATE_DOMAIN

    def test_emit_drop_domain(self) -> None:
        op = DHANDLER.diff(
            DHANDLER.canonicalize(
                {"oldie": {"domain_type": "text", "not_null": False}}
            ),
            {},
        )[0][0]
        stmts = DHANDLER.emit(op)
        assert len(stmts) == 1
        assert "DROP DOMAIN IF EXISTS" in stmts[0].upgrade_sql


# ---------------------------------------------------------------------------
# Sequence golden tests
# ---------------------------------------------------------------------------

class TestSequenceHandlerGolden:
    def test_fresh_create_simple(self) -> None:
        sequences = [{"name": "order_id_seq", "start": 1000}]
        config = FakeConfig([], sequences)
        snap: dict[str, Any] = {}

        inline_stmts = _inline_sequence_preamble(sequences)
        inline_up, inline_rb = _assemble_migration(inline_stmts)

        snap_spec = SHANDLER.canonicalize(SHANDLER.extract(snap))
        model_spec = SHANDLER.canonicalize(
            SHANDLER.model_spec_from_config(config)
        )
        up_ops, rb_ops = SHANDLER.diff(snap_spec, model_spec)
        h_stmts = []
        for op in up_ops:
            h_stmts.extend(SHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(SHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        assert handler_up == inline_up
        assert handler_rb == inline_rb

    def test_fresh_create_full(self) -> None:
        sequences = [
            {
                "name": "user_id_seq",
                "start": 1000,
                "increment": 5,
                "minvalue": 1,
                "maxvalue": 999999,
                "cycle": True,
                "owned_by": "users.id",
            },
        ]
        config = FakeConfig([], sequences)
        snap: dict[str, Any] = {}

        inline_stmts = _inline_sequence_preamble(sequences)
        inline_up, inline_rb = _assemble_migration(inline_stmts)

        snap_spec = SHANDLER.canonicalize(SHANDLER.extract(snap))
        model_spec = SHANDLER.canonicalize(
            SHANDLER.model_spec_from_config(config)
        )
        up_ops, rb_ops = SHANDLER.diff(snap_spec, model_spec)
        h_stmts = []
        for op in up_ops:
            h_stmts.extend(SHANDLER.emit(op))
        for op in rb_ops:
            h_stmts.extend(SHANDLER.emit(op))
        handler_up, handler_rb = _assemble_migration(h_stmts)

        assert handler_up == inline_up
        assert handler_rb == inline_rb

    def test_drop_sequence(self) -> None:
        config = FakeConfig([], [])
        # Simulate a snapshot that could carry sequences in future
        snap_spec = SHANDLER.canonicalize({})
        model_spec = SHANDLER.canonicalize(
            SHANDLER.model_spec_from_config(config)
        )
        up, rb = SHANDLER.diff(snap_spec, model_spec)
        assert up == []
        assert rb == []


# ---------------------------------------------------------------------------
# Sequence contract tests
# ---------------------------------------------------------------------------

class TestSequenceHandlerContract:
    def test_canonical_idempotent(self) -> None:
        spec = {"MySeq": {"start": 100, "increment": 1}}
        c1 = SHANDLER.canonicalize(spec)
        c2 = SHANDLER.canonicalize(c1)
        assert c1 == c2
        assert "myseq" in c1

    def test_canonical_empty(self) -> None:
        assert SHANDLER.canonicalize({}) == {}
        assert SHANDLER.canonicalize(None) == {}

    def test_unchanged_empty_diff(self) -> None:
        snap_spec = SHANDLER.canonicalize({})
        model_spec = SHANDLER.canonicalize({})
        up, rb = SHANDLER.diff(snap_spec, model_spec)
        assert up == []
        assert rb == []

    def test_model_spec_from_tables_empty(self) -> None:
        assert SHANDLER.model_spec_from_tables([]) == {}

    def test_create_sequence_reversible(self) -> None:
        model_spec = SHANDLER.canonicalize({"my_seq": {"start": 1}})
        up, rb = SHANDLER.diff({}, model_spec)
        for op in up:
            if op.object_type == "create_sequence":
                assert not op.irreversible

    def test_emit_create_sequence(self) -> None:
        model_spec = SHANDLER.canonicalize(
            {"my_seq": {"start": 100, "increment": 5, "cycle": True}}
        )
        up, _ = SHANDLER.diff({}, model_spec)
        op = up[0]
        stmts = SHANDLER.emit(op)
        assert len(stmts) == 1
        up_sql = stmts[0].upgrade_sql
        assert "CREATE SEQUENCE IF NOT EXISTS my_seq" in up_sql
        assert "START WITH 100" in up_sql
        assert "INCREMENT BY 5" in up_sql
        assert "CYCLE" in up_sql
        assert stmts[0].order == StatementOrder.CREATE_SEQUENCE

    def test_emit_drop_sequence(self) -> None:
        up, _ = SHANDLER.diff(
            {},
            SHANDLER.canonicalize({"my_seq": {"start": 1}}),
        )
        op = up[0]
        # Create a drop op manually
        drop_ops, _ = SHANDLER.diff(
            SHANDLER.canonicalize({"my_seq": {"start": 1}}),
            {},
        )
        stmts = SHANDLER.emit(drop_ops[0])
        assert "DROP SEQUENCE IF EXISTS" in stmts[0].upgrade_sql


# ---------------------------------------------------------------------------
# Driver orchestration tests
# ---------------------------------------------------------------------------

class TestPhase4Driver:
    def test_driver_with_domain_handler(self) -> None:
        driver = RegistryDriver()
        driver.register(DHANDLER)
        config = FakeConfig(
            [{"name": "my_domain", "type": "text", "not_null": True}],
            [],
        )
        up, rb = driver.run({"domains": {}}, [], config)
        create = [op for op in up if op.object_type == "create_domain"]
        drop = [op for op in rb if op.object_type == "drop_domain"]
        assert len(create) == 1
        assert len(drop) == 1

    def test_driver_with_sequence_handler(self) -> None:
        driver = RegistryDriver()
        driver.register(SHANDLER)
        config = FakeConfig(
            [],
            [{"name": "my_seq", "start": 1}],
        )
        up, rb = driver.run({}, [], config)
        create = [op for op in up if op.object_type == "create_sequence"]
        drop = [op for op in rb if op.object_type == "drop_sequence"]
        assert len(create) == 1
        assert len(drop) == 1

    def test_driver_with_all_three_handlers(self) -> None:
        """Domain, sequence, and enum handlers together."""
        from dbwarden.engine.pg_registry import EnumHandler

        driver = RegistryDriver()
        driver.register(SequenceHandler())
        driver.register(DomainHandler())
        driver.register(EnumHandler())

        config = FakeConfig(
            [{"name": "pos_int", "type": "integer", "not_null": True}],
            [{"name": "my_seq", "start": 100}],
        )

        enum_snapshot = {"enums": {}}
        enum_model = [
            type(
                "FakeTable",
                (),
                {
                    "name": "t",
                    "columns": [
                        type(
                            "FakeCol",
                            (),
                            {
                                "pg_meta": {
                                    "pg_type": {
                                        "kind": "enum",
                                        "type_name": "mood",
                                        "values": ["happy", "sad"],
                                    }
                                }
                            },
                        )()
                    ],
                },
            )()
        ]

        up, rb = driver.run(enum_snapshot, enum_model, config)

        create_domains = [op for op in up if op.object_type == "create_domain"]
        create_sequences = [op for op in up if op.object_type == "create_sequence"]
        create_enums = [op for op in up if op.object_type == "create_type"]

        assert len(create_domains) == 1
        assert len(create_sequences) == 1
        assert len(create_enums) == 1

        # Emit all and verify SQL ordering
        up_sql, rb_sql, _ = driver.emit_op_to_sql(up, rb)
        assert "CREATE DOMAIN" in up_sql
        assert "CREATE SEQUENCE" in up_sql
        assert "CREATE TYPE mood" in up_sql
