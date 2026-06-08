import pytest
from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.safety import analyze_schema
from dbwarden.commands.check import check_cmd


def test_analyze_schema_detect_add_column():
    model_tables = [
        ModelTable(
            name="users",
            columns=[ModelColumn("email", "VARCHAR(255)", True, False, False, None, None)],
        )
    ]

    snapshot = {
        "users": {
            "columns": {},
            "object_type": "table",
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert len(issues) == 1
    assert issues[0].change_type == "add_column"


def test_analyze_schema_detect_column_type_change():
    model_tables = [
        ModelTable(
            name="users",
            columns=[ModelColumn("email", "TEXT", True, False, False, None, None)],
        )
    ]

    snapshot = {
        "users": {
            "columns": {"email": {"type": "VARCHAR(255)", "nullable": True, "default": None}},
            "object_type": "table",
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert len(issues) == 1
    assert issues[0].change_type == "change_column_type"


def test_analyze_schema_detect_add_comment():
    model_tables = [
        ModelTable(
            name="users",
            columns=[ModelColumn("email", "VARCHAR(255)", True, False, False, None, None)],
            comment="User email addresses",
        )
    ]

    snapshot = {
        "users": {
            "columns": {"email": {"type": "VARCHAR(255)", "nullable": True, "default": None}},
            "object_type": "table",
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert any(i.change_type == "change_table_comment" for i in issues)


def test_analyze_schema_detect_pg_column_meta_change():
    col = ModelColumn("email", "VARCHAR(255)", False, False, False, None, None,
                       comment="New email",
                       pg_meta={"pg_collation": "en_US.UTF-8"})

    model_tables = [
        ModelTable(name="users", columns=[col])
    ]

    snapshot = {
        "users": {
            "columns": {
                "email": {"type": "VARCHAR(255)", "nullable": False, "default": None,
                          "comment": "Old email", "pg_column": {"collation": "C"}}
            },
            "object_type": "table",
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert any(i.change_type == "change_pg_column_meta" for i in issues)


def test_analyze_schema_add_projection_is_info():
    model_tables = [
        ModelTable(
            name="posts",
            columns=[ModelColumn("author", "String", False, False, False, None, None)],
            clickhouse_options={
                "ch_projections": [
                    {"name": "by_author", "query": "SELECT * ORDER BY author"}
                ]
            },
        )
    ]

    snapshot = {
        "posts": {
            "object_type": "table",
            "columns": {"author": {"type": "String", "nullable": False, "default": None}},
            "clickhouse_options": {},
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert len(issues) == 1
    assert issues[0].severity == "INFO"
    assert issues[0].change_type == "add_projection"


def test_analyze_schema_ttl_change_is_warning():
    model_tables = [
        ModelTable(
            name="events",
            columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
            clickhouse_options={
                "ch_ttl": ["event_time + INTERVAL 1 MONTH DELETE"],
            },
        )
    ]

    snapshot = {
        "events": {
            "object_type": "table",
            "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
            "clickhouse_options": {
                "ch_ttl": ["event_time + INTERVAL 1 YEAR DELETE"],
            },
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert len(issues) == 1
    assert issues[0].severity == "WARNING"
    assert issues[0].required_flag == "--force"


def test_analyze_schema_partition_change_is_error():
    model_tables = [
        ModelTable(
            name="events",
            columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
            clickhouse_options={
                "ch_partition_by": "toYYYYMM(event_time)",
            },
        )
    ]

    snapshot = {
        "events": {
            "object_type": "table",
            "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
            "clickhouse_options": {
                "ch_partition_by": "toYYYYMM(created_at)",
            },
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    assert len(issues) == 1
    assert issues[0].severity == "ERROR"


def test_check_cmd_requires_force_for_warning(monkeypatch):
    monkeypatch.setattr(
        "dbwarden.commands.check.load_issues",
        lambda database=None: [
            analyze_schema(
                [
                    ModelTable(
                        name="events",
                        columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
                        clickhouse_options={"ch_ttl": ["new_ttl"]},
                    )
                ],
                {
                    "events": {
                        "object_type": "table",
                        "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
                        "clickhouse_options": {"ch_ttl": ["old_ttl"]},
                    }
                },
            )[0]
        ],
    )

    try:
        check_cmd(output_format="txt", force=False)
    except RuntimeError as exc:
        assert "require --force" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_check_cmd_allows_warning_with_force(monkeypatch):
    monkeypatch.setattr(
        "dbwarden.commands.check.load_issues",
        lambda database=None: [
            analyze_schema(
                [
                    ModelTable(
                        name="events",
                        columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
                        clickhouse_options={"ch_ttl": ["new_ttl"]},
                    )
                ],
                {
                    "events": {
                        "object_type": "table",
                        "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
                        "clickhouse_options": {"ch_ttl": ["old_ttl"]},
                    }
                },
            )[0]
        ],
    )

    check_cmd(output_format="json", force=True)


def test_analyze_schema_replicated_engine_change_is_warning():
    model_tables = [
        ModelTable(
            name="events",
            columns=[ModelColumn("id", "UInt64", False, True, False, None, None)],
            clickhouse_options={
                "ch_engine": "ReplicatedMergeTree",
                "ch_zookeeper_path": "'/clickhouse/tables/shard1'",
                "ch_replica_name": "'{replica}'",
            },
        )
    ]

    snapshot = {
        "events": {
            "object_type": "table",
            "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
            "clickhouse_options": {
                "ch_zookeeper_path": "'/clickhouse/tables/old_path'",
                "ch_replica_name": "'{replica}'",
            },
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    zk_issues = [i for i in issues if i.change_type == "clickhouse_zookeeper_path"]
    assert len(zk_issues) == 1
    assert zk_issues[0].severity == "WARNING"
    assert zk_issues[0].required_flag == "--force"


def test_analyze_schema_dictionary_create_is_info():
    model_tables = [
        ModelTable(
            name="country_codes",
            columns=[ModelColumn("code", "String", False, True, False, None, None)],
            clickhouse_options={
                "ch_dictionary": True,
                "ch_dict_layout": "FLAT()",
                "ch_dict_source": "CLICKHOUSE(HOST 'localhost' TABLE 'countries')",
                "ch_dict_lifetime": "MIN 0 MAX 3600",
            },
            object_type="dictionary",
        )
    ]

    snapshot = {}

    issues = analyze_schema(model_tables, snapshot)

    create_issues = [i for i in issues if i.change_type == "create_table"]
    assert len(create_issues) == 1
    assert create_issues[0].severity == "INFO"
    assert "dictionary" in create_issues[0].message


def test_analyze_schema_dictionary_source_change_is_warning():
    model_tables = [
        ModelTable(
            name="country_codes",
            columns=[ModelColumn("code", "String", False, True, False, None, None)],
            clickhouse_options={
                "ch_dictionary": True,
                "ch_dict_layout": "FLAT()",
                "ch_dict_source": "CLICKHOUSE(HOST 'new_host' TABLE 'countries')",
                "ch_dict_lifetime": "MIN 0 MAX 3600",
            },
            object_type="dictionary",
        )
    ]

    snapshot = {
        "country_codes": {
            "object_type": "dictionary",
            "columns": {"code": {"type": "String", "nullable": False, "default": None}},
            "clickhouse_options": {
                "ch_dict_source": "CLICKHOUSE(HOST 'old_host' TABLE 'countries')",
            },
        }
    }

    issues = analyze_schema(model_tables, snapshot)

    source_issues = [i for i in issues if i.change_type == "clickhouse_dict_source"]
    assert len(source_issues) == 1
    assert source_issues[0].severity == "WARNING"
    assert source_issues[0].required_flag == "--force"
