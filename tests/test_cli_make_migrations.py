from unittest.mock import patch

from typer.testing import CliRunner

from dbwarden.cli.main import app


def test_make_migrations_rename_flag_accepted():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "add email",
                "--rename", "users.name:email",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["rename_flags"] == ["users.name:email"]
        assert kwargs["rename_table_flags"] == []
        assert kwargs["safe_type_change"] is False
        assert kwargs["description"] == "add email"


def test_make_migrations_rename_table_flag_accepted():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "rename users",
                "--rename-table", "users:accounts",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["rename_table_flags"] == ["users:accounts"]
        assert kwargs["rename_flags"] == []


def test_make_migrations_safe_type_change_flag():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "safe type change",
                "--safe-type-change",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["safe_type_change"] is True


def test_make_migrations_all_flags_combined():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "bulk changes",
                "--rename", "users.name:full_name",
                "--rename", "posts.title:headline",
                "--rename-table", "users:accounts",
                "--safe-type-change",
                "--plan",
                "--verbose",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["rename_flags"] == ["users.name:full_name", "posts.title:headline"]
        assert kwargs["rename_table_flags"] == ["users:accounts"]
        assert kwargs["safe_type_change"] is True
        assert kwargs["output_plan"] is True
        assert kwargs["verbose"] is True


def test_make_migrations_rename_table_multiple():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "rename tables",
                "--rename-table", "users:accounts",
                "--rename-table", "posts:articles",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["rename_table_flags"] == ["users:accounts", "posts:articles"]


def test_make_migrations_with_database():
    runner = CliRunner()
    with patch("dbwarden.cli.main.handle_make_migrations") as mock:
        with patch("dbwarden.cli.main.validate_directory"):
            result = runner.invoke(app, [
                "make-migrations", "init",
                "--database", "primary",
            ])
        assert result.exit_code == 0
        _, kwargs = mock.call_args
        assert kwargs["database"] == "primary"
