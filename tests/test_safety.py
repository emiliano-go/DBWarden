from dbwarden.commands.check import check_cmd
from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.safety import analyze_schema


def test_analyze_schema_add_projection_is_info():
    model_tables = [
        ModelTable(
            name="posts",
            columns=[ModelColumn("author", "String", False, False, False, None, None)],
            clickhouse_options={
                "clickhouse_projections": [
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
                "clickhouse_ttl": ["event_time + INTERVAL 1 MONTH DELETE"],
            },
        )
    ]

    snapshot = {
        "events": {
            "object_type": "table",
            "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
            "clickhouse_options": {
                "clickhouse_ttl": ["event_time + INTERVAL 1 YEAR DELETE"],
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
                "clickhouse_partition_by": "toYYYYMM(event_time)",
            },
        )
    ]

    snapshot = {
        "events": {
            "object_type": "table",
            "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
            "clickhouse_options": {
                "clickhouse_partition_by": "toYYYYMM(created_at)",
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
                        clickhouse_options={"clickhouse_ttl": ["new_ttl"]},
                    )
                ],
                {
                    "events": {
                        "object_type": "table",
                        "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
                        "clickhouse_options": {"clickhouse_ttl": ["old_ttl"]},
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
                        clickhouse_options={"clickhouse_ttl": ["new_ttl"]},
                    )
                ],
                {
                    "events": {
                        "object_type": "table",
                        "columns": {"id": {"type": "UInt64", "nullable": False, "default": None}},
                        "clickhouse_options": {"clickhouse_ttl": ["old_ttl"]},
                    }
                },
            )[0]
        ],
    )

    check_cmd(output_format="json", force=True)
