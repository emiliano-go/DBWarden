import os
import tempfile

from dbwarden.commands.make_migrations import generate_migration_sql
from dbwarden.engine.model_discovery import ModelColumn, ModelTable


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

        upgrade_sql, rollback_sql = generate_migration_sql(
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

        upgrade_sql, rollback_sql = generate_migration_sql(
            [table], migrations_dir=tmpdir
        )

        assert "ALTER TABLE users ADD COLUMN email" in upgrade_sql
        assert "CREATE TABLE IF NOT EXISTS users" not in upgrade_sql
        assert "ALTER TABLE users DROP COLUMN email" in rollback_sql
