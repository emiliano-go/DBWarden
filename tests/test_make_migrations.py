import os
import tempfile
import json
from pathlib import Path

from dbwarden.commands.make_migrations import (
    RenameIntent,
    _parse_rename_flags,
    build_migration_plan,
    generate_migration_sql,
    make_migrations_cmd,
)
from dbwarden.config import set_dev_mode
from dbwarden.engine.model_discovery import ModelColumn, ModelTable
from dbwarden.engine.migration_name import Change


def _write_migration(directory: str, name: str, content: str) -> None:
    with open(os.path.join(directory, name), "w", encoding="utf-8") as f:
        f.write(content)


def test_generate_migration_sql_skips_duplicate_create_from_pending_migration():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_migration(
            tmpdir,
            "0002_auto_generated.sql",
            """-- upgrade

CREATE TABLE IF NOT EXISTS uploads (
    upload_id UUID NOT NULL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    filename VARCHAR NOT NULL
)

-- rollback

DROP TABLE uploads
""",
        )

        table = ModelTable(
            name="uploads",
            columns=[
                ModelColumn("upload_id", "UUID", False, True, False, None, None),
                ModelColumn("user_id", "VARCHAR", False, False, False, None, None),
                ModelColumn("filename", "VARCHAR", False, False, False, None, None),
            ],
        )

        upgrade_sql, rollback_sql, _ = generate_migration_sql(
            [table], migrations_dir=tmpdir
        )

        assert upgrade_sql.strip() == ""
        assert rollback_sql.strip() == ""


def test_generate_migration_sql_uses_pending_migrations_as_schema_source():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_migration(
            tmpdir,
            "0001_create_users.sql",
            """-- upgrade

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY
)

-- rollback

DROP TABLE users
""",
        )

        table = ModelTable(
            name="users",
            columns=[
                ModelColumn("id", "INTEGER", False, True, False, None, None),
                ModelColumn("email", "VARCHAR(255)", False, False, True, None, None),
            ],
        )

        upgrade_sql, rollback_sql, _ = generate_migration_sql(
            [table], migrations_dir=tmpdir
        )

        assert "ALTER TABLE users ADD COLUMN email" in upgrade_sql
        assert "CREATE TABLE IF NOT EXISTS users" not in upgrade_sql
        assert "ALTER TABLE users DROP COLUMN email" in rollback_sql


def test_build_migration_plan_includes_operations_and_checksum():
    plan = build_migration_plan(
        migration_id="primary__0001_add_users_age",
        changes=[Change(operation="add_column", table="users", target="age")],
        upgrade_sql="ALTER TABLE users ADD COLUMN age INTEGER",
    )

    assert plan["migration_id"] == "primary__0001_add_users_age"
    assert plan["required_flags"] == []
    assert plan["operations"] == [
        {
            "type": "add_column",
            "table": "users",
            "column": "age",
            "severity": "INFO",
        }
    ]
    assert isinstance(plan["checksum"], str)
    assert plan["checksum"]


def test_make_migrations_writes_plan_file_next_to_sql():
    set_dev_mode(False)
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            Path("dbwarden.py").write_text(
                "from dbwarden import database_config\n\n"
                "database_config(database_name='primary', default=True, database_type='sqlite', database_url_sync='sqlite:///./app.db', model_paths=['models'])\n",
                encoding="utf-8",
            )
            Path("migrations/primary").mkdir(parents=True)
            Path("models").mkdir(parents=True)
            Path("models/user.py").write_text(
                "from sqlalchemy import Column, Integer, String\n"
                "from sqlalchemy.orm import declarative_base\n\n"
                "Base = declarative_base()\n\n"
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id = Column(Integer, primary_key=True)\n"
                "    email = Column(String(255), nullable=False, unique=True)\n",
                encoding="utf-8",
            )

            make_migrations_cmd(database="primary")

            sql_files = sorted(Path("migrations/primary").glob("*.sql"))
            plan_files = sorted(Path("migrations/primary").glob("*.plan.json"))

            assert len(sql_files) == 1
            assert len(plan_files) == 1
            assert plan_files[0].name == sql_files[0].with_suffix(".plan.json").name

            plan = json.loads(plan_files[0].read_text(encoding="utf-8"))
            assert plan["migration_id"] == sql_files[0].stem
            assert plan["operations"]
            assert plan["checksum"]
        finally:
            os.chdir(old_cwd)


def test_parse_rename_flags_valid():
    result = _parse_rename_flags(["users.name:full_name", "posts.title:headline"])
    assert len(result) == 2
    assert result[0] == RenameIntent("users", "name", "full_name")
    assert result[1] == RenameIntent("posts", "title", "headline")


def test_parse_rename_flags_invalid_format():
    import pytest
    with pytest.raises(ValueError, match="Invalid --rename format"):
        _parse_rename_flags(["badformat"])


def test_parse_rename_flags_missing_new_name():
    import pytest
    with pytest.raises(ValueError, match="Invalid --rename format"):
        _parse_rename_flags(["users.name:"])


def test_build_plan_operation_includes_resolved_from():
    plan = build_migration_plan(
        migration_id="test__0001_rename",
        changes=[
            Change(operation="rename_column", table="users", target="email",
                   resolved_from="rename_flag"),
        ],
        upgrade_sql="ALTER TABLE users RENAME COLUMN name TO email",
    )
    op = plan["operations"][0]
    assert op["resolved_from"] == "rename_flag"
    assert op["type"] == "rename_column"
    assert op["new_name"] == "email"


def test_build_plan_operation_omits_resolved_from_when_none():
    plan = build_migration_plan(
        migration_id="test__0001_add",
        changes=[
            Change(operation="add_column", table="users", target="age"),
        ],
        upgrade_sql="ALTER TABLE users ADD COLUMN age INTEGER",
    )
    assert "resolved_from" not in plan["operations"][0]
